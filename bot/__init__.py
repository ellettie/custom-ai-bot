import discord
from discord.app_commands import describe
from discord.ext import commands
import os
import logging
from typing import Optional
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
    await ctx.response.defer(thinking=True)
    parts: list[dict] = [{"text": text}]
    file_msg: Optional[discord.WebhookMessage] = None
    if file is not None:
        if file.content_type not in ALLOWED_MIME:
            await ctx.followup.send("サポートされていないファイル形式です。")
            return
        data = await file.read()
        file_msg = await ctx.followup.send(file=await file.to_file())
        parts.insert(0, {
            "file_data": {"mime_type": file.content_type, "data": data}
        })
    response:str = await gemini.generate_text(parts) # type: ignore
    header = f"**{ctx.user.display_name}**: {text}\n\n"
    content = f"**{bot.user.name}**の回答:\n{response}" #type: ignore
    chunks = await myutils.split_message(header + content)
    for idx, chunk in enumerate(chunks):
        if idx == 0 and file_msg is not None:
            await file_msg.edit(content=chunk)
        else:
            await ctx.followup.send(content=chunk)
    
@bot.tree.command(
    name="image",
    description="画像を生成"
)
@describe(prompt="生成する画像の説明")
async def image(ctx: discord.Interaction, prompt: str):
    await ctx.response.defer(thinking=True)
    path, text = await gemini.generate_image(prompt)
    if path is not None:
        await ctx.followup.send(content=f"**{ctx.user.display_name}**: {prompt}", file=discord.File(path))
        os.remove(path)
    else:
        await ctx.followup.send(content=f"**エラーが発生しました**: {text}")
        
@bot.tree.command(
    name="info",
    description="Botの情報を確認"
)
async def info(ctx: discord.Interaction):
    text = f"チャットモデル: {gemini.MODEL}\n画像生成モデル: {gemini.IMAGE_MODEL}"
    await ctx.response.send_message(text)
    
@bot.event
async def on_ready() -> None:
    print("Bot is ready!")
    
def run():
    bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG) # type: ignore

if __name__ == "__main__":
    run()
