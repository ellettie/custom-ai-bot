import discord
import os

class Config:
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
    BOTTON_TIMEOUT = 21600.0