import discord
from .config import Config

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