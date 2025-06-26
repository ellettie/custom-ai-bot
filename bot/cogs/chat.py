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
    def __init__(self, *, history: list[dict]):
        super().__init__(
            label = "返信する",
            emoji = "💬",
            style = discord.ButtonStyle.primary
        )
        self.history: bytes = myutils.compress_history(history)
        
    async def callback(self, interaction: discord.Interaction):
        modal = ReplyModal(
            original_itx=interaction,
            history=self.history
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
        self.button.disabled = True
        if self.message:
            channel = await self.bot.fetch_channel(self.message.channel.id)
            if isinstance(channel, discord.TextChannel):
                message = await channel.fetch_message(self.message.id)
                try:
                    await message.edit(view=None)
                    self.button.history = b''
                except Exception as e:
                    print(f"メッセージ編集エラー: {e}")


class ReplyModal(discord.ui.Modal, title='AIに返信'):
    def __init__(self, original_itx: discord.Interaction, history: bytes):
        super().__init__()
        self.original_itx = original_itx
        self.history = history
        self.cog: "ChatCog" = original_itx.client.get_cog("ChatCog") # type: ignore

    reply_text = discord.ui.TextInput(
        label='返信内容', style=discord.TextStyle.paragraph,
        placeholder='ここに返信を入力してください...', required=True, max_length=2000
    )

    async def on_submit(self, ctx: discord.Interaction):
        await ctx.response.defer(thinking=True)
        history = myutils.decompress_history(self.history)
        try:           
            user_message = self.reply_text.value
            response, input_token, output_token = await gemini.generate_text([{"text": f"{ctx.user.display_name}: {user_message}"}], history)
            logger.info(f"{ctx.id}: {{input_token: {input_token}, output_token: {output_token}}}")
            
            # ★ 修正点: 次の応答のために、新しいプロンプト(user_message)を渡す
            await self.cog._send_response(ctx, user_prompt=user_message, response=response, history=history)

        except gemini.errors.APIError as e:
            await ctx.followup.send(embed=myutils.get_error_embed(gemini.get_error_message(e)))
            logger.error(f"{ctx.id} : Reply raised an API error. {e}")
        except Exception as e:
            await ctx.followup.send(embed=myutils.get_error_embed("エラーが発生しました"))
            logger.exception(f"{ctx.id} : Reply raised an Exception. {e}")


# --- Cogクラス ---

class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    # ★ 修正点: headerの代わりにuser_promptを受け取るように変更
    async def _send_response(self, ctx: discord.Interaction, user_prompt: str, response: str, history: Optional[list[dict]]=None, view_tokens: bool = False,
                             input_token: Optional[int] = None, output_token: Optional[int] = None,
                             file_to_attach: Optional[discord.File] = None):
        """応答を分割して送信するためのヘルパーメソッド"""
        # ヘッダーはこのメソッド内で生成する
        header = f"**{ctx.user.display_name}**: {user_prompt}\n\n"
        if history is None:
            history = []
        response_for_hist = response.split(Config.RESPONSE_SEPARATOR)[0]
        history.insert(0, {"user": header[:-2], "ai": response_for_hist})
        if len(history) > 10:
            history.pop()
        logger.debug(history)
        
        webhook_message: Optional[discord.WebhookMessage] = None
        if file_to_attach:
            webhook_message = await ctx.followup.send(file=file_to_attach, wait=True)

        chunks = myutils.split_message(response)
        for i, chunk in enumerate(chunks):
            is_last_chunk = (i == len(chunks) - 1)
            embed = discord.Embed(description=chunk, colour=Config.EMBED_SET["answer"]["colour"])
            
            if is_last_chunk and view_tokens:
                embed.set_footer(text=f"input_token: {input_token} output_token: {output_token}")

            # ★ 修正点: user_promptもViewに渡す
            view = ReplyView(button=ReplyButton(history=history), bot=self.bot) if is_last_chunk else discord.utils.MISSING

            if i == 0:
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar) # type: ignore
                if webhook_message:
                    msg = await webhook_message.edit(content=header, embed=embed, view=view)
                else:
                    msg = await ctx.followup.send(content=header, embed=embed, view=view)
            else:
                msg= await ctx.followup.send(embed=embed, view=view)
            if is_last_chunk:
                view.message = msg

    @app_commands.command(name="ask", description="AIに質問する")
    @describe(text="質問内容", file="ファイルを添付 (画像/音声)", view_tokens="入出力トークンを表示")
    async def ask(self, ctx: discord.Interaction, text: str, file: Optional[discord.Attachment] = None, view_tokens: bool = False):
        if len(text) > Config.MAX_PROMPT_LEN:
            return await ctx.response.send_message(embed=myutils.get_error_embed("質問が長すぎます"), ephemeral=True)
        
        await ctx.response.defer(thinking=True)
        parts: list[dict] = [{"text": f"**{ctx.user.display_name}**: {text}"}]
        file_to_resend: Optional[discord.File] = None

        if file:
            if file.content_type not in Config.ALLOWED_MIME:
                return await ctx.followup.send(embed=myutils.get_error_embed("サポートされていないファイル形式です"), ephemeral=True)
            file_to_resend = await file.to_file()
            parts.insert(0, {"file_data": {"mime_type": file.content_type, "data": await file.read()}})

        try:
            response, input_token, output_token = await gemini.generate_text(parts)
            logger.info(f"{ctx.id}: {{input_token: {input_token}, output_token: {output_token}}}")
            
            # ★ 修正点: headerを直接渡す代わりに、生の質問テキスト(text)をuser_promptとして渡す
            await self._send_response(ctx, user_prompt=text, response=response, view_tokens=view_tokens, 
                                      input_token=input_token, output_token=output_token, file_to_attach=file_to_resend)

        except gemini.errors.APIError as e:
            await ctx.followup.send(embed=myutils.get_error_embed(gemini.get_error_message(e)))
            logger.error(f"{ctx.id} : /ask raised an API error. {e}")
        except Exception as e:
            await ctx.followup.send(embed=myutils.get_error_embed("エラーが発生しました"))
            logger.exception(f"{ctx.id} : /ask raised an Exception. {e}")

    @app_commands.command(name="image", description="画像を生成")
    @describe(prompt="生成する画像の説明", view_token="入出力トークンを表示する")
    async def image(self, ctx: discord.Interaction, prompt: str, view_token: bool = False):
        if len(prompt) > Config.MAX_PROMPT_LEN:
            return await ctx.response.send_message(embed=myutils.get_error_embed("プロンプトが長すぎます"), ephemeral=True)
        
        await ctx.response.defer(thinking=True)
        try:
            path, text, input_token, output_token = await gemini.generate_image(prompt)
            logger.info(f"{ctx.id}: {{input_token: {input_token}, output_token: {output_token}}}")

            if path:
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                file = discord.File(path, filename)
                embed = discord.Embed(title=prompt, description=text, colour=Config.EMBED_SET["image"]["colour"])
                embed.set_image(url=f"attachment://{filename}")
                if view_token:
                    embed.set_footer(text=f"input_token: {input_token} output_token: {output_token}")
                await ctx.followup.send(embed=embed, file=file)
                os.remove(path)
            else:
                await ctx.followup.send(embed=myutils.get_error_embed("画像の生成に失敗しました。"))

        except gemini.errors.APIError as e:
            await ctx.followup.send(embed=myutils.get_error_embed(gemini.get_error_message(e)))
            logger.error(f"{ctx.id} : /image raised an API error. {e}")
        except Exception as e:
            await ctx.followup.send(embed=myutils.get_error_embed("エラーが発生しました"))
            logger.exception(f"{ctx.id} : /image raised an Exception. {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))