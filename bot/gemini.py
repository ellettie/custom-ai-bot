from google import genai
from google.genai import errors
from google.genai import types
import os
from io import BytesIO
from PIL import Image
import mimetypes
import tempfile

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("MODEL", "gemini-2.0-flash")
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation")

client = genai.Client(api_key=GEMINI_API_KEY)

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

async def generate_image(prompt: str):
    response = await client.aio.models.generate_content(
        model=IMAGE_MODEL,
        contents=(prompt),
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

async def generate_text(parts: list[dict], history=None):
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
    
    contents = [
        types.Content(
            role="user",
            parts=part_objs
        )
    ]
    if history is not None:
        for chat in history:
            contents.insert(
                0,
                types.Content(
                    role="model",
                    parts=[
                        types.Part.from_text(text=chat["ai"])
                    ]
                )
            )
            contents.insert(
                0,
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=chat["user"])
                    ]
                )
            )
    grounding_tool = types.Tool(
        google_search=types.GoogleSearch()
    )
    url_context_tool = types.Tool(
        url_context=types.UrlContext()
    )
    generate_content_config = types.GenerateContentConfig(
        # tools=[grounding_tool, url_context_tool],
        tools=[grounding_tool],
        response_mime_type="text/plain",
    )
    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=contents, # type: ignore
        config=generate_content_config,
    )
    text = add_citations(response)
    input_token = getattr(response.usage_metadata, "prompt_token_count", None)
    output_token = getattr(response.usage_metadata, "candidates_token_count", None)
    return text or "エラーが発生しました", input_token, output_token

def add_citations(response) -> str:
    text = response.text
    gm = getattr(response.candidates[0], "grounding_metadata", None)
    if not gm or not gm.grounding_supports:
        return text                
    supports = gm.grounding_supports
    chunks   = gm.grounding_chunks

    # Sort supports by end_index in descending order to avoid shifting issues when inserting.
    sorted_supports = sorted(supports, key=lambda s: s.segment.end_index, reverse=True)

    for support in sorted_supports:
        end_index = support.segment.end_index
        if support.grounding_chunk_indices:
            # Create citation string like [1](link1)[2](link2)
            citation_links = []
            for i in support.grounding_chunk_indices:
                if i < len(chunks):
                    uri = chunks[i].web.uri
                    citation_links.append(f"[{i + 1}]({uri})")

            citation_string = ", ".join(citation_links)
            text = text[:end_index] + citation_string + text[end_index:]

    return text

def get_error_message(e: errors.APIError) -> str:
    if e.code == 429:
        desc = f"**{e.code}**\n\n{e.message}\nAPIレートリミットに達しました。しばらくお待ちください"
    elif e.code == 503:
        desc = f"**{e.code}**\n\n{e.message}\nAPIサービスが混雑しています。時間を置いて再度試してください"
    else:
        desc = f"**{e.code}**\n\n{e.message}"
        
    return desc
