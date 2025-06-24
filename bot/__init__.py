import discord
from discord.app_commands import describe
from discord.ext import commands
import os
import logging
from typing import Optional
from datetime import datetime
from . import gemini
from . import myutils
from .config import Config

logger = logging.getLogger(__name__)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

class CUSTOM_AI_BOT(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="$", intents=intents)
        
    async def setup_hook(self):
        guild = discord.Object(id=Config.GUILD_ID)
        try:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        except Exception as e:
            logger.exception(f"failed to add slash commands when starting\n{e}")
            
    async def on_guild_join(self, guild: discord.Object):
        if guild.id != Config.GUILD_ID:
            await guild.leave() # type: ignore
            logger.warning(f"leaved from unauthorized guild {guild.id}")
        else:
            try:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"bot joined to {guild.id}")
            except Exception as e:
                logger.exception(f"failed to add slash commands when joining to {guild.id}\n{e}")               
bot = CUSTOM_AI_BOT()

@bot.tree.command(
    name="ask",
    description="AIに質問する",
)
@describe(text="質問内容")
@describe(file="ファイルを添付 画像ファイル 対応形式: PNG/JPEG/WEBP/HEIC/HEIF 音声ファイル 対応形式: WAV/MP3/AIFF/AAC/OGG Vorbis/FLAC")
@describe(view_tokens="入出力トークンを表示")
async def ask(ctx:discord.Interaction, text:str, file: Optional[discord.Attachment]=None, view_tokens: bool=False) -> None:
    if len(text) > Config.MAX_PROMPT_LEN:
        await ctx.response.defer(ephemeral=True, thinking=True)
        await ctx.followup.send(embed=myutils.get_error_embed("質問が長すぎます"))
        return
    parts: list[dict] = [{"text": text}]
    if file is not None:
        if file.content_type not in Config.ALLOWED_MIME:
            await ctx.response.defer(ephemeral=True, thinking=True)
            await ctx.followup.send(embed=myutils.get_error_embed("サポートされていないファイル形式です"))
            return
        data = await file.read()
        await ctx.response.defer(thinking=True)
        parts.insert(0, {
            "file_data": {"mime_type": file.content_type, "data": data}
        })
    else:
        await ctx.response.defer(thinking=True)
    try:
        response, input_token, output_token = await gemini.generate_text(parts)
        logger.info(f"{ctx.id}: {{input_token: {input_token}, output_token: {output_token}}}")
    except gemini.errors.APIError as e:
        await ctx.followup.send(embed=myutils.get_error_embed(gemini.get_error_message(e)))
        logger.error(f"{ctx.id} : /ask raised an API error. {e}")
        return
    except Exception as e:
        await ctx.followup.send(embed=myutils.get_error_embed("エラーが発生しました"))
        logger.exception(f"{ctx.id} : /ask raised an Exception. {e}")
        return
    header = f"**{ctx.user.display_name}**: {text}\n\n"
    chunks = await myutils.split_message(response)
    file_msg: Optional[discord.WebhookMessage] = None
    if file is not None:
        file_msg = await ctx.followup.send(file=await file.to_file())
    for idx, chunk in enumerate(chunks):
        embed = discord.Embed(description=chunk, colour=Config.EMBED_SET["answer"]["colour"]) # type: ignore
        if idx == len(chunks) -1 and view_tokens:
            embed.set_footer(text=f"input_token: {input_token} output_token: {output_token}")
        if idx == 0:
            embed.set_author(
                name=bot.user.name, # type: ignore
                icon_url=bot.user.display_avatar # type: ignore
            )
            if file_msg:
                await file_msg.edit(content=header, embed=embed)
            else:
                await ctx.followup.send(content=header, embed=embed)
        else:
            await ctx.followup.send(embed=embed)
    
@bot.tree.command(
    name="image",
    description="画像を生成"
)
@describe(prompt="生成する画像の説明")
@describe(view_token="入出力トークンを表示する")
async def image(ctx: discord.Interaction, prompt: str, view_token: bool=False):
    if len(prompt) > Config.MAX_PROMPT_LEN:
        await ctx.response.defer(ephemeral=True, thinking=True)
        await ctx.followup.send(embed=myutils.get_error_embed("プロンプトが長すぎます"))
        return
    await ctx.response.defer(thinking=True)
    try:
        path, text, input_token, output_token = await gemini.generate_image(prompt)
        logger.info(f"{ctx.id}: {{input_token: {input_token}, output_token: {output_token}}}")
    except gemini.errors.APIError as e:
        await ctx.followup.send(embed=myutils.get_error_embed(gemini.get_error_message(e)))
        logger.error(f"{ctx.id} : /image raised an API error. {e}")
        return
    except Exception as e:
        await ctx.followup.send(embed=myutils.get_error_embed("エラーが発生しました"))
        logger.exception(f"{ctx.id} : /image raised an Exception. {e}")
        return
    if path is not None:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{now}.png"
        file = discord.File(path, filename)
        embed = discord.Embed(title=prompt, description=text, colour=Config.EMBED_SET["image"]["colour"])
        embed.set_image(url=f"attachment://{filename}")
        if view_token:
            embed.set_footer(text=f"input_token: {input_token} output_token: {output_token}")
        await ctx.followup.send(embed=embed, file=file)
        os.remove(path)
    else:
        await ctx.followup.send(embed=myutils.get_error_embed("エラーが発生しました"))
        
@bot.tree.command(
    name="info",
    description="Botの情報を確認"
)
async def info(ctx: discord.Interaction):
    text = f"**チャットモデル**: {gemini.MODEL}\n**画像生成モデル**: {gemini.IMAGE_MODEL}"
    embed = discord.Embed(
        title=Config.EMBED_SET["info"]["title"],
        description=text,
        colour=Config.EMBED_SET["info"]["colour"],
        )
    embed.set_author(
        name=bot.user.name, # type: ignore
        icon_url=bot.user.display_avatar # type: ignore
    )
    embed.set_footer(text="developed by ellettie")
    await ctx.response.send_message(embed=embed)
    
@bot.tree.command(
    name="help",
    description="/コマンド一覧"
)
async def help(ctx: discord.Interaction):
    embed = Config.HELP_EMBED.copy()
    embed.set_author(
        name=bot.user.name, # type: ignore
        icon_url=bot.user.display_avatar # type: ignore
    )
    embed.set_footer(text="developed by ellettie")
    await ctx.response.send_message(embed=embed)
    
@bot.event
async def on_ready() -> None:
    print("Bot is ready!")
    
def run(level=logging.WARNING):
    bot.run(Config.TOKEN, log_handler=handler, log_level=level) # type: ignore
