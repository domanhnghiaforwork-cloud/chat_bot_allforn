from google import genai
from google.genai import types

from app.config.prompts import SUMMARY_PROMPT
from app.config.settings import get_settings
from app.db.models import Message
from app.memory.context_builder import ChatContext
from app.utils.token_counter import count_tokens


class GeminiServiceError(RuntimeError):
    pass


async def generate_reply(context: ChatContext) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiServiceError("GEMINI_API_KEY chưa được cấu hình")

    try:
        async with genai.Client(api_key=settings.gemini_api_key).aio as client:
            token_count = await count_tokens(
                client,
                settings.gemini_model,
                context.contents,
                context.system_instruction,
            )
            if token_count > settings.max_input_tokens:
                raise GeminiServiceError("Ngữ cảnh hội thoại vượt giới hạn token")

            response = await client.models.generate_content(
                model=settings.gemini_model,
                contents=context.contents,
                config=types.GenerateContentConfig(
                    system_instruction=context.system_instruction,
                    max_output_tokens=settings.max_output_tokens,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
        answer = response.text
    except GeminiServiceError:
        raise
    except Exception as exc:
        raise GeminiServiceError("Không thể nhận phản hồi từ Gemini") from exc

    if not answer:
        raise GeminiServiceError("Gemini không trả về nội dung")

    return answer


async def generate_summary(previous_summary: str, messages: list[Message]) -> str:
    settings = get_settings()
    transcript = "\n".join(f"{message.role}: {message.content}" for message in messages)
    prompt = (
        f"{SUMMARY_PROMPT}\n\nBản tóm tắt hiện tại:\n{previous_summary or '(chưa có)'}"
        f"\n\nĐoạn hội thoại mới:\n{transcript}"
    )

    try:
        async with genai.Client(api_key=settings.gemini_api_key).aio as client:
            response = await client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=512,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
        summary = response.text
    except Exception as exc:
        raise GeminiServiceError("Không thể tóm tắt hội thoại") from exc

    if not summary:
        raise GeminiServiceError("Gemini không trả về bản tóm tắt")
    return summary
