import discord
import os

class Config:
    GUILD_ID = int(os.environ.get("GUILD_ID", 0))
    TOKEN= os.environ.get("TOKEN", "")
    ALLOWED_IMAGE_MIME: set[str] = {
        "image/png", 
        "image/jpeg", 
        "image/webp",
        "image/heic", 
        "image/heif",
    }
    ALLOWED_AUDIO_MIME: set[str] = {
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
    LOGO = r"""
┌──────────────────────────────────────────────────────────────┐
│ ██████\  ██\   ██\  ██████\ ████████\  ██████\  ██\      ██\ │
│██  __██\ ██ |  ██ |██  __██\\__██  __|██  __██\ ███\    ███ |│
│██ /  \__|██ |  ██ |██ /  \__|  ██ |   ██ /  ██ |████\  ████ |│
│██ |      ██ |  ██ |\██████\    ██ |   ██ |  ██ |██\██\██ ██ |│
│██ |      ██ |  ██ | \____██\   ██ |   ██ |  ██ |██ \███  ██ |│
│██ |  ██\ ██ |  ██ |██\   ██ |  ██ |   ██ |  ██ |██ |\█  /██ |│
│\██████  |\██████  |\██████  |  ██ |    ██████  |██ | \_/ ██ |│
│ \______/  \______/  \______/   \__|    \______/ \__|     \__|│
│                                                              │
│                                                              │
│                                                              │
│ ██████\  ██████\       ███████\   ██████\ ████████\          │
│██  __██\ \_██  _|      ██  __██\ ██  __██\\__██  __|         │
│██ /  ██ |  ██ |        ██ |  ██ |██ /  ██ |  ██ |            │
│████████ |  ██ |        ███████\ |██ |  ██ |  ██ |            │
│██  __██ |  ██ |        ██  __██\ ██ |  ██ |  ██ |            │
│██ |  ██ |  ██ |        ██ |  ██ |██ |  ██ |  ██ |            │
│██ |  ██ |██████\       ███████  | ██████  |  ██ |            │
│\__|  \__|\______|      \_______/  \______/   \__|            │
└──────────────────────────────────────────────────────────────┘
"""
    VERSION = "0.2.5"
    REPO_URL  = "https://github.com/ellettie/custom-ai-bot"
    AUTHOR    = "ellettie"
    
    RESPONSE_SEPARATOR = "\n\n**—— 参考リンク ——**\n"
