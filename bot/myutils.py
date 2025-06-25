import discord
import google.genai
import PIL
from .config import Config
import os
import sys
import time
import logging

def split_message(text, max_length=1900):
    if len(text) <= max_length:
        return [text] 
    chunks = []
    current_chunk = ""
    lines = text.split('\n')
    for line in lines:
        # 行が長すぎる場合は文で分割
        if len(line) > max_length:
            sentences = line.split('。')
            for sentence in sentences:
                if sentence:  # 空でない場合
                    sentence = sentence + '。' if not sentence.endswith('。') else sentence
                    
                    if len(current_chunk + sentence) > max_length:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = sentence
                        else:
                            # 1文が長すぎる場合は強制分割
                            chunks.append(sentence[:max_length])
                            current_chunk = sentence[max_length:]
                    else:
                        current_chunk += sentence
        else:
            if len(current_chunk + '\n' + line) > max_length:
                chunks.append(current_chunk.strip())
                current_chunk = line
            else:
                current_chunk += '\n' + line if current_chunk else line
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def get_error_embed(description: str) -> discord.Embed:
    return discord.Embed(
        title=Config.EMBED_SET["error"]["title"], 
        description=description, 
        colour=Config.EMBED_SET["error"]["colour"])
    
def rgb(r, g, b): return f"\x1b[38;2;{r};{g};{b}m"  # 前景
LOGO = rgb(114, 137, 218)
GREEN  = rgb(80, 255, 180)
GREY   = rgb(180, 180, 180)
RESET  = "\x1b[0m"

def print_banner(bot, start_ts: float) -> None:
    print(f"{LOGO}{Config.LOGO}")

    rows = [
        (f"{LOGO}version{RESET}",     Config.VERSION),
        (f"{LOGO}repo{RESET}",     Config.REPO_URL),
        (f"{LOGO}developer{RESET}",     Config.AUTHOR),
    ]
    for key, val in rows:
        print(f" {key:<10} : {GREY}{val}{RESET}")
    print()
    rows = [
        (f"{GREEN}python{RESET}",   f"{sys.version_info.major}.{sys.version_info.minor}"),
        (f"{GREEN}discord.py{RESET}", discord.__version__),
        (f"{GREEN}google-genai{RESET}", google.genai.__version__),
        (f"{GREEN}pillow{RESET}", PIL.__version__),
        (f"{GREEN}user{RESET}",     f"{bot.user} ({bot.user.id})"),          # type: ignore
        (f"{GREEN}guild{RESET}",   bot.guild_id),
        (f"{GREEN}logLevel{RESET}", logging.getLevelName(logging.getLogger().level)),
        (f"{GREEN}startup{RESET}",  f"{time.perf_counter() - start_ts:.2f}s"),
    ]
    for key, val in rows:
        print(f" {key:<10} : {GREY}{val}{RESET}")
