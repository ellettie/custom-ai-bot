import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import describe
import os
import logging
from typing import Optional
from datetime import datetime

from .. import gemini
from .. import myutils
from ..config import Config

logger = logging.getLogger(__name__)

# --- 返信用のUIコンポーネント ---
class ReplyButton(discord.ui.Button):
    def __init__(self, *, chat_id: int, last_idx: int):
        super().__init__(
            label = "返信する",
            emoji = "💬",
            style = discord.ButtonStyle.primary
        )
        self.chat_id = chat_id
        self.last_idx = last_idx
        self.is_replied = False
        
    async def callback(self, interaction: discord.Interaction):
        modal = ReplyModal(
            original_itx=interaction,
            button=self
        )
        await interaction.response.send_modal(modal)

class ReplyView(discord.ui.View):
    def __init__(self, *, button: ReplyButton, bot: commands.Bot):
        super().__init__(timeout=Config.BOTTON_TIMEOUT)
        self.button = button
        self.add_item(button)
        self.message: Optional[discord.WebhookMessage] = None
        self.bot = bot
        
    async def on_timeout(self):
        if not self.button.is_replied:
            gemini.delete_chat(self.button.chat_id)
        self.button.disabled = True
        if self.message:
            channel = await self.bot.fetch_channel(self.message.channel.id)
            if isinstance(channel, discord.TextChannel):
                message = await channel.fetch_message(self.message.id)
                try:
                    await message.edit(view=None)
                except Exception as e:
                    print(f"メッセージ編集エラー: {e}")


class ReplyModal(discord.ui.Modal, title='AIに返信'):
    def __init__(self, original_itx: discord.Interaction, button: ReplyButton):
        super().__init__()
        self.original_itx = original_itx
        self.button = button
        self.cog: "ChatCog" = original_itx.client.get_cog("ChatCog") # type: ignore

    reply_text = discord.ui.TextInput(
        label='返信内容', style=discord.TextStyle.paragraph,
        placeholder='ここに返信を入力してください...', required=True, max_length=2000
    )

    async def on_submit(self, itx: discord.Interaction):
        if self.button.is_replied:
            id = itx.id
            parent_id = self.button.chat_id
            last_idx = self.button.last_idx
        else:
            id = self.button.chat_id
            parent_id = None
            last_idx = None
        await itx.response.defer(thinking=True)
        try:           
            user_message = self.reply_text.value
            response, input_token, output_token, last_idx = await gemini.generate_text(
                parts=[{"text": f"{itx.user.display_name}: {user_message}"}],
                id=id,
                parent_id=parent_id,
                last_idx=last_idx,
                is_new_chat=self.button.is_replied
                )
            logger.info(f"{itx.id}: {{input_token: {input_token}, output_token: {output_token}}}")
            self.button.is_replied = True
            await self.cog._send_response(itx, user_prompt=user_message, response=response, chat_id=id, last_idx=last_idx)

        except gemini.errors.APIError as e:
            await itx.followup.send(embed=myutils.get_error_embed(gemini.get_error_message(e)))
            logger.error(f"{itx.id} : Reply raised an API error. {e}")
        except Exception as e:
            await itx.followup.send(embed=myutils.get_error_embed("エラーが発生しました"))
            logger.exception(f"{itx.id} : Reply raised an Exception. {e}")


# --- Cogクラス ---

class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    async def _send_response(self, itx: discord.Interaction, user_prompt: str, response: str, chat_id: int, last_idx: int, view_tokens: bool = False,
                             input_token: Optional[int] = None, output_token: Optional[int] = None,
                             file_to_attach: Optional[discord.File] = None):
        """応答を分割して送信するためのヘルパーメソッド"""
        header = f"**{itx.user.display_name}**: {user_prompt}\n\n"
        
        webhook_message: Optional[discord.WebhookMessage] = None
        if file_to_attach:
            webhook_message = await itx.followup.send(file=file_to_attach, wait=True)

        chunks = myutils.split_message(response)
        for i, chunk in enumerate(chunks):
            is_last_chunk = (i == len(chunks) - 1)
            embed = discord.Embed(description=chunk, colour=Config.EMBED_SET["answer"]["colour"])
            
            if is_last_chunk and view_tokens:
                embed.set_footer(text=f"input_token: {input_token} output_token: {output_token}")

            view = ReplyView(button=ReplyButton(chat_id=chat_id, last_idx=last_idx), bot=self.bot) if is_last_chunk else discord.utils.MISSING

            if i == 0:
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar) # type: ignore
                if webhook_message:
                    msg = await webhook_message.edit(content=header, embed=embed, view=view)
                else:
                    msg = await itx.followup.send(content=header, embed=embed, view=view)
            else:
                msg= await itx.followup.send(embed=embed, view=view)
            if is_last_chunk:
                view.message = msg

    @app_commands.command(name="ask", description="AIに質問する")
    @describe(text="質問内容", file="ファイルを添付 (画像/音声)", view_tokens="入出力トークンを表示")
    async def ask(self, itx: discord.Interaction, text: str, file: Optional[discord.Attachment] = None, view_tokens: bool = False):
        if len(text) > Config.MAX_PROMPT_LEN:
            return await itx.response.send_message(embed=myutils.get_error_embed("質問が長すぎます"), ephemeral=True)
        
        await itx.response.defer(thinking=True)
        parts: list[dict] = [{"text": f"**{itx.user.display_name}**: {text}"}]
        file_to_resend: Optional[discord.File] = None

        if file:
            if file.content_type not in Config.ALLOWED_IMAGE_MIME and file.content_type not in Config.ALLOWED_AUDIO_MIME:
                return await itx.followup.send(embed=myutils.get_error_embed("サポートされていないファイル形式です"), ephemeral=True)
            file_to_resend = await file.to_file()
            parts.insert(0, {"file_data": {"mime_type": file.content_type, "data": await file.read()}})

        try:
            response, input_token, output_token, last_idx = await gemini.generate_text(parts=parts, id=itx.id, is_new_chat=True)
            logger.info(f"{itx.id}: {{input_token: {input_token}, output_token: {output_token}}}")
            
            await self._send_response(itx, user_prompt=text, response=response, chat_id=itx.id, last_idx=last_idx, view_tokens=view_tokens, 
                                      input_token=input_token, output_token=output_token, file_to_attach=file_to_resend)

        except gemini.errors.APIError as e:
            await itx.followup.send(embed=myutils.get_error_embed(gemini.get_error_message(e)))
            logger.error(f"{itx.id} : /ask raised an API error. {e}")
        except Exception as e:
            await itx.followup.send(embed=myutils.get_error_embed("エラーが発生しました"))
            logger.exception(f"{itx.id} : /ask raised an Exception. {e}")

    @app_commands.command(name="image", description="画像を生成")
    @describe(prompt="生成する画像の説明", file="ファイルを添付 (画像のみ)", file2="追加のファイルを添付 (画像のみ)", view_token="入出力トークンを表示する")
    async def image(
        self, 
        itx: discord.Interaction, 
        prompt: str, 
        file: Optional[discord.Attachment] = None, 
        file2: Optional[discord.Attachment] = None, 
        view_token: bool = False
        ):
        if len(prompt) > Config.MAX_PROMPT_LEN:
            return await itx.response.send_message(embed=myutils.get_error_embed("プロンプトが長すぎます"), ephemeral=True)
        
        await itx.response.defer(thinking=True)
        parts: list[dict] = [{"text": prompt}]
        file_to_resends: Optional[list[discord.File]] = []

        if file2:
            if file2.content_type not in Config.ALLOWED_IMAGE_MIME:
                return await itx.followup.send(embed=myutils.get_error_embed("サポートされていないファイル形式です"), ephemeral=True)
            file_to_resends.insert(0, await file2.to_file())
            parts.insert(0, {"file_data": {"mime_type": file2.content_type, "data": await file2.read()}})
        if file:
            if file.content_type not in Config.ALLOWED_IMAGE_MIME:
                return await itx.followup.send(embed=myutils.get_error_embed("サポートされていないファイル形式です"), ephemeral=True)
            file_to_resends.insert(0, await file.to_file())
            parts.insert(0, {"file_data": {"mime_type": file.content_type, "data": await file.read()}})
        try:
            path, text, input_token, output_token = await gemini.generate_image(parts)
            logger.info(f"{itx.id}: {{input_token: {input_token}, output_token: {output_token}}}")

            if path:
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                output_file = discord.File(path, filename)
                embed = discord.Embed(title=prompt, description=text, colour=Config.EMBED_SET["image"]["colour"])
                embed.set_image(url=f"attachment://{filename}")
                if view_token:
                    embed.set_footer(text=f"input_token: {input_token} output_token: {output_token}")
                if len(file_to_resends) > 0:
                    file_to_resends.append(output_file)
                    await itx.followup.send(embed=embed, files=file_to_resends)
                else:
                    await itx.followup.send(embed=embed, file=output_file)
                os.remove(path)
            else:
                await itx.followup.send(embed=myutils.get_error_embed("画像の生成に失敗しました。"))

        except gemini.errors.APIError as e:
            await itx.followup.send(embed=myutils.get_error_embed(gemini.get_error_message(e)))
            logger.error(f"{itx.id} : /image raised an API error. {e}")
        except Exception as e:
            await itx.followup.send(embed=myutils.get_error_embed("エラーが発生しました"))
            logger.exception(f"{itx.id} : /image raised an Exception. {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))