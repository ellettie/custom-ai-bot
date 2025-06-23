import discord
from discord.app_commands import describe
from discord.ext import commands
import os
import logging
from typing import Optional
from datetime import datetime
from . import gemini
from . import myutils

GUILD_ID = int(os.environ.get("GUILD_ID", 0))
TOKEN= os.environ.get("TOKEN", "")
ALLOWED_MIME: set[str] = {
    "image/png", 
    "image/jpeg", 
    "image/webp",
    "image/heic", 
    "image/heif",
    "audio/vnd.wave",  
    "audio/wav", "audio/x-wav",
    "audio/mpeg",       
    "audio/mp3",     
    "audio/x-aiff", "audio/aiff",
    "audio/aac", "audio/x-aac",
    "audio/ogg",
    "audio/flac", "audio/x-flac",
}
MAX_PROMPT_LEN = 1800
EMBED_SET: dict = {
    "error": {"title": "Error", "colour": discord.Colour.red()},
    "answer": {"title": "Answer", "colour": discord.Colour.blue()},
    "image": {"title": "Image", "colour": discord.Colour.green()},
    "info": {"title": "Info", "colour": discord.Colour.gold()},
    "help": {"title": "Help", "colour": discord.Colour.pink()},
}
HELP_TEXT = """スラッシュコマンドを通してGEMINI APIを利用できます
- **/ask**: AIに質問します 画像か音声ファイルを添付できます
- **/image**: 画像を生成します
- **/info**: モデルの情報を取得します
- **/help**: /コマンドの情報を取得します"""
HELP_EMBED = discord.Embed(
    title=EMBED_SET["help"]["title"],
    description=HELP_TEXT,
    colour=EMBED_SET["help"]["colour"],
)

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
        guild = discord.Object(id=GUILD_ID)
        try:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        except Exception as e:
            logger.exception(f"failed to add slash commands when starting\n{e}")
            
    async def on_guild_join(self, guild: discord.Object):
        if guild.id != GUILD_ID:
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
@describe(file="ファイルを添付    画像ファイル 対応形式: PNG/JPEG/WEBP/HEIC/HEIF 音声ファイル 対応形式: WAV/MP3/AIFF/AAC/OGG Vorbis/FLAC")
async def ask(ctx:discord.Interaction, text:str, file: Optional[discord.Attachment]=None) -> None:
    if len(text) > MAX_PROMPT_LEN:
        await ctx.response.defer(ephemeral=True, thinking=True)
        await ctx.followup.send(embed=discord.Embed(
            title=EMBED_SET["error"]["title"],
            description="質問が長すぎます",
            colour=EMBED_SET["error"]["colour"]
            ), ephemeral=True)
        return
    parts: list[dict] = [{"text": text}]
    file_msg: Optional[discord.WebhookMessage] = None
    if file is not None:
        if file.content_type not in ALLOWED_MIME:
            await ctx.response.defer(ephemeral=True, thinking=True)
            await ctx.followup.send(embed=discord.Embed(
                title=EMBED_SET["error"]["title"],
                description="サポートされていないファイル形式です",
                colour=EMBED_SET["error"]["colour"]
                ), ephemeral=True)
            return
        data = await file.read()
        await ctx.response.defer(thinking=True)
        file_msg = await ctx.followup.send(file=await file.to_file())
        parts.insert(0, {
            "file_data": {"mime_type": file.content_type, "data": data}
        })
    else:
        await ctx.response.defer(thinking=True)
    response: str = await gemini.generate_text(parts) # type: ignore
    header = f"**{ctx.user.display_name}**: {text}\n\n"
    # content = f"**{bot.user.name}**の回答:\n{response}" #type: ignore
    chunks = await myutils.split_message(response)
    for idx, chunk in enumerate(chunks):
        embed = discord.Embed(description=chunk, colour=EMBED_SET["answer"]["colour"]) # type: ignore
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
async def image(ctx: discord.Interaction, prompt: str):
    if len(prompt) > MAX_PROMPT_LEN:
        await ctx.response.defer(ephemeral=True, thinking=True)
        await ctx.followup.send(embed=discord.Embed(
            title=EMBED_SET["error"]["title"],
            description="プロンプトがが長すぎます",
            colour=EMBED_SET["error"]["colour"]
            ), ephemeral=True)
        return
    await ctx.response.defer(thinking=True)
    path, text = await gemini.generate_image(prompt)
    if path is not None:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{now}.png"
        file = discord.File(path, filename)
        embed = discord.Embed(title=prompt, description=text, colour=EMBED_SET["image"]["colour"])
        embed.set_image(url=f"attachment://{filename}")
        await ctx.followup.send(embed=embed, file=file)
        os.remove(path)
    else:
        await ctx.followup.send(embed=discord.Embed(
            title=EMBED_SET["error"]["title"],
            description="エラーが発生しました",
            colour=EMBED_SET["error"]["colour"]
        ))
        
@bot.tree.command(
    name="info",
    description="Botの情報を確認"
)
async def info(ctx: discord.Interaction):
    text = f"**チャットモデル**: {gemini.MODEL}\n**画像生成モデル**: {gemini.IMAGE_MODEL}"
    embed = discord.Embed(
        title=EMBED_SET["info"]["title"],
        description=text,
        colour=EMBED_SET["info"]["colour"],
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
    HELP_EMBED.set_author(
        name=bot.user.name, # type: ignore
        icon_url=bot.user.display_avatar # type: ignore
    )
    HELP_EMBED.set_footer(text="developed by ellettie")
    await ctx.response.send_message(embed=HELP_EMBED)
    
@bot.event
async def on_ready() -> None:
    print("Bot is ready!")
    
def run():
    bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG) # type: ignore

if __name__ == "__main__":
    run()
