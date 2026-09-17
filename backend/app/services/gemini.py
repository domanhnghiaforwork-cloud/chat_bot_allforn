from google import genai
from google.genai import types

from app.config.prompts import SUMMARY_PROMPT
from app.config.settings import get_settings
from app.db.models import Message
from app.memory.context_builder import ChatContext, messages_to_contents
from app.utils.token_counter import count_tokens


class GeminiServiceError(RuntimeError):
    pass


async def _count(contents, system_instruction: str | None = None) -> int:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiServiceError("GEMINI_API_KEY chưa được cấu hình")
    try:
        async with genai.Client(api_key=settings.gemini_api_key).aio as client:
            return await count_tokens(
                client,
                settings.gemini_model,
                contents,
                system_instruction,
            )
    except Exception as exc:
        raise GeminiServiceError("Không thể đếm token") from exc


async def count_text_tokens(text: str) -> int:
    return await _count(text) if text else 0


async def count_message_tokens(messages: list[Message]) -> int:
    if not messages:
        return 0
    return await _count(messages_to_contents(messages))


async def count_context_tokens(context: ChatContext) -> int:
    return await _count(context.contents, context.system_instruction)


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
            if token_count > settings.max_chat_input_tokens:
                raise GeminiServiceError("Ngữ cảnh hội thoại vượt giới hạn token")

            response = await client.models.generate_content(
                model=settings.gemini_model,
                contents=context.contents,
                config=types.GenerateContentConfig(
                    system_instruction=context.system_instruction,
                    max_output_tokens=settings.max_chat_output_tokens,
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


def _summary_prompt(
    previous_summary: str,
    messages: list[Message],
    max_tokens: int,
) -> str:
    transcript = "\n".join(f"{message.role}: {message.content}" for message in messages)
    return (
        f"{SUMMARY_PROMPT}\nBản tóm tắt mới không vượt quá {max_tokens} token."
        f"\n\nBản tóm tắt hiện tại:\n{previous_summary or '(chưa có)'}"
        f"\n\nĐoạn hội thoại mới:\n{transcript or '(không có)'}"
    )


def _complete_prefix_sizes(messages: list[Message]) -> list[int]:
    """Các kích thước batch không tách cặp user - assistant."""
    return [
        index
        for index in range(1, len(messages) + 1)
        if index == len(messages)
        or not (
            messages[index - 1].role == "user"
            and messages[index].role == "assistant"
        )
    ]


async def generate_summary(previous_summary: str, messages: list[Message]) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiServiceError("GEMINI_API_KEY chưa được cấu hình")

    try:
        async with genai.Client(api_key=settings.gemini_api_key).aio as client:
            summary = previous_summary
            pending = messages.copy()
            first_run = True

            while pending or first_run:
                first_run = False
                sizes = _complete_prefix_sizes(pending)

                if not sizes:
                    take = 0
                    prompt = _summary_prompt(
                        summary,
                        [],
                        settings.max_history_summary_tokens,
                    )
                    if (
                        await count_tokens(client, settings.gemini_model, prompt)
                        > settings.max_summary_input_tokens
                    ):
                        raise GeminiServiceError(
                            "Summary cũ quá lớn để nén trong context của model summary"
                        )
                else:
                    # Chọn batch hoàn chỉnh lớn nhất vừa ngân sách input summary.
                    left, right = 0, len(sizes) - 1
                    take = 0
                    prompt = ""
                    while left <= right:
                        middle = (left + right) // 2
                        candidate_take = sizes[middle]
                        candidate_prompt = _summary_prompt(
                            summary,
                            pending[:candidate_take],
                            settings.max_history_summary_tokens,
                        )
                        if (
                            await count_tokens(
                                client, settings.gemini_model, candidate_prompt
                            )
                            <= settings.max_summary_input_tokens
                        ):
                            take = candidate_take
                            prompt = candidate_prompt
                            left = middle + 1
                        else:
                            right = middle - 1

                    if take == 0:
                        raise GeminiServiceError(
                            "Một cặp message quá lớn cho context của model summary"
                        )

                response = await client.models.generate_content(
                    model=settings.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=settings.max_history_summary_tokens,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        ),
                    ),
                )
                summary = response.text or ""
                pending = pending[take:]
    except Exception as exc:
        if isinstance(exc, GeminiServiceError):
            raise
        raise GeminiServiceError("Không thể tóm tắt hội thoại") from exc

    if not summary:
        raise GeminiServiceError("Gemini không trả về bản tóm tắt")
    return summary
