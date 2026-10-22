import os
import base64
from typing import Optional

# gemini-1.5-* models are retired; the model is configurable so it can be bumped without code changes.
DEFAULT_MODEL = "gemini-2.5-flash"

_client = None


def is_enabled() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL)


def generate(
    prompt: str,
    image_b64: Optional[str] = None,
    mime_type: str = "image/jpeg",
    json_output: bool = False,
) -> str:
    """
    Sends a prompt (plus an optional image) to Gemini via the google-genai SDK.
    With json_output=True the API is asked for application/json, so no markdown
    fences need to be stripped from the reply.
    """
    global _client
    from google import genai
    from google.genai import types

    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    contents = [prompt]
    if image_b64:
        contents.append(types.Part.from_bytes(data=base64.b64decode(image_b64), mime_type=mime_type))

    config = types.GenerateContentConfig(
        temperature=0.0 if json_output else 0.3,
        response_mime_type="application/json" if json_output else None,
    )
    response = _client.models.generate_content(model=model_name(), contents=contents, config=config)
    return (response.text or "").strip()
