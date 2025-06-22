from google import genai
from google.genai import types
import os
from io import BytesIO
from PIL import Image
import mimetypes
import tempfile

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("MODEL", "gemma-3-27b-it")
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
    image_path = None
    text = ""
    for part in response.candidates[0].content.parts: # type: ignore
        if part.text is not None:
            text = part.text
        if part.inline_data and part.inline_data.data:
            image_path = save_image_to_temp(part.inline_data)
            break
    return image_path, text

async def generate_text(text: str):
    contents = types.Content(
        role="user",
        parts=[
            types.Part.from_text(text=text)
        ],
    )
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
    )
    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=contents,
        config=generate_content_config,
    )
    return response.text or "エラーが発生しました"

