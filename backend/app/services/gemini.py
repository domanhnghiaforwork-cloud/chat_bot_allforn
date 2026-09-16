from google import genai
from google.genai import types

from app.config.settings import get_settings


class GeminiServiceError(RuntimeError):
    pass


async def generate_reply(message: str) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiServiceError("GEMINI_API_KEY chưa được cấu hình")

    try:
        async with genai.Client(api_key=settings.gemini_api_key).aio as client:
            response = await client.models.generate_content(
                model=settings.gemini_model,
                contents=message,
                config=types.GenerateContentConfig(
                    max_output_tokens=settings.max_output_tokens,
                ),
            )
        answer = response.text
    except Exception as exc:
        raise GeminiServiceError("Không thể nhận phản hồi từ Gemini") from exc

    if not answer:
        raise GeminiServiceError("Gemini không trả về nội dung")

    return answer
