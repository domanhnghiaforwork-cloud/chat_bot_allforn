"""Adapter tương thích v3; mọi lời gọi thật được chuyển vào LLMGateway."""

from app.llm.errors import LLMError
from app.llm.gateway import LLMGateway
from app.memory.context_builder import ChatContext
from app.models import Message

GeminiServiceError = LLMError


async def count_text_tokens(text: str, gateway: LLMGateway) -> int:
    return await gateway.count_text_tokens(text)


async def count_message_tokens(messages: list[Message], gateway: LLMGateway) -> int:
    return await gateway.count_message_tokens(messages)


async def count_context_tokens(context: ChatContext, gateway: LLMGateway) -> int:
    return await gateway.count_context_tokens(context)


async def generate_reply(context: ChatContext, gateway: LLMGateway) -> str:
    return (await gateway.generate_once(context)).text


async def generate_summary(
    previous_summary: str, messages: list[Message], gateway: LLMGateway
) -> str:
    return await gateway.generate_summary(previous_summary, messages)
