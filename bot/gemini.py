from google import genai
from google.genai import errors
from google.genai import types
import os
from io import BytesIO
from PIL import Image
import mimetypes
import tempfile
from .config import Config

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation")

client = genai.Client(api_key=GEMINI_API_KEY)
chats = {}

def save_image_to_temp(inline_data) -> str:
    """BytesIO から PIL で開いて、一時ファイルに保存。パスを返す。"""
    img = Image.open(BytesIO(inline_data.data))
    suffix = mimetypes.guess_extension(inline_data.mime_type) or ".png"
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        img.save(path)
    finally:
        os.close(fd)
    return path

def create_part_objs(parts: list[dict]) -> types.Content:
    """
    parts = [
        {"file_data": {"mime_type": file mime type, "data": file byte data}},
        {"text": "prompt"}
    ]
    """
    part_objs = []
    for part in parts:
        if "text" in part:
            part_objs.append(types.Part.from_text(text=part["text"]))
        elif "file_data" in part:
            part_objs.append(types.Part.from_bytes(
                mime_type=part["file_data"]["mime_type"],
                data=part["file_data"]["data"]
            ))
    
    contents = types.Content(
            role="user",
            parts=part_objs,
        )
    return contents

def create_chat(parent_id: int | None = None, last_idx: int | None = None):
    if parent_id is not None:
        history = chats[parent_id].get_history()[:last_idx]
    else:
        history = None
    grounding_tool = types.Tool(
        google_search=types.GoogleSearch()
    )
    url_context_tool = types.Tool(
        url_context=types.UrlContext()
    )
    generate_content_config = types.GenerateContentConfig(
        tools=[grounding_tool, url_context_tool],
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(text="""あなたは優秀なAIアシスタントです。回答は指定がない限り日本語でしてください。
                                 ユーザの質問は以下のように構造化されています。<**ユーザの名前**>: <質問内容>""")
        ],
    )
    chat = client.aio.chats.create(
        model=MODEL,
        config=generate_content_config,
        history=history
    )
    return chat

def delete_chat(id: int):
    del chats[id]

async def generate_image(parts: list[dict]):
    contents = create_part_objs(parts)
    response = await client.aio.models.generate_content(
        model=IMAGE_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        )
    )
    input_token = getattr(response.usage_metadata, "prompt_token_count", None)
    output_token = getattr(response.usage_metadata, "candidates_token_count", None)
    image_path = None
    text = ""
    for part in response.candidates[0].content.parts: # type: ignore
        if part.text is not None:
            text = part.text
        if part.inline_data and part.inline_data.data:
            image_path = save_image_to_temp(part.inline_data)
            break
    return image_path, text, input_token, output_token

async def generate_text(
        parts: list[dict], 
        id: int, 
        parent_id: int | None = None,
        last_idx: int | None = None,
        is_new_chat: bool = False
        ):
    contents = create_part_objs(parts)
    if is_new_chat:
        chats[id] = create_chat(parent_id, last_idx)
    response = await chats[id].send_message(
        message = contents.parts
    )
    text = add_citations(response)
    input_token = getattr(response.usage_metadata, "prompt_token_count", None)
    output_token = getattr(response.usage_metadata, "candidates_token_count", None)
    last_idx = len(chats[id].get_history())
    return text or "エラーが発生しました", input_token, output_token, last_idx

def add_citations(response) -> str:
    text = response.text.rstrip()
    gm = getattr(response.candidates[0], "grounding_metadata", None)
    if not gm or not gm.grounding_supports or gm.grounding_chunks is None:
        return text

    seen, links = set(), []
    for support in gm.grounding_supports:
        for i in support.grounding_chunk_indices:
            if i < len(gm.grounding_chunks):
                uri = gm.grounding_chunks[i].web.uri
                if uri not in seen:
                    seen.add(uri)
                    links.append(uri)

    if not links:
        return text
    footnotes = ", ".join(f"[{n}]({url})" for n, url in enumerate(links, 1))
    separator = Config.RESPONSE_SEPARATOR
    return f"{text}{separator}{footnotes}"


def get_error_message(e: errors.APIError) -> str:
    if e.code == 429:
        desc = f"**{e.code}**\n\n{e.message}\nAPIレートリミットに達しました。しばらくお待ちください"
    elif e.code == 503:
        desc = f"**{e.code}**\n\n{e.message}\nAPIサービスが混雑しています。時間を置いて再度試してください"
    else:
        desc = f"**{e.code}**\n\n{e.message}"
    return desc
