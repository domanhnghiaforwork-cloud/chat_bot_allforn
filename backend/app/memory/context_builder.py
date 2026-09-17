from dataclasses import dataclass

from google.genai import types

from app.config.prompts import SYSTEM_PROMPT
from app.models import Message


@dataclass(slots=True)
class ChatContext:
    system_instruction: str
    contents: list[types.Content]


def build_system_instruction(summary: str | None) -> str:
    system_instruction = SYSTEM_PROMPT
    if summary:
        system_instruction += f"\n\nTóm tắt hội thoại trước đó:\n{summary}"
    return system_instruction


def messages_to_contents(messages: list[Message]) -> list[types.Content]:
    # Gemini dùng role "model" cho câu trả lời của assistant.
    return [
        types.Content(
            role="model" if message.role == "assistant" else "user",
            parts=[types.Part.from_text(text=message.content)],
        )
        for message in messages
    ]


def build_context(summary: str | None, messages: list[Message], question: str) -> ChatContext:
    contents = messages_to_contents(messages)
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=question)])
    )
    return ChatContext(
        system_instruction=build_system_instruction(summary),
        contents=contents,
    )
