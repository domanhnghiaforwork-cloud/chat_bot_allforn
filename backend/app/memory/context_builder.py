from dataclasses import dataclass

from google.genai import types

from app.config.prompts import SYSTEM_PROMPT
from app.db.models import Message


@dataclass(slots=True)
class ChatContext:
    system_instruction: str
    contents: list[types.Content]


def build_context(summary: str | None, messages: list[Message], question: str) -> ChatContext:
    system_instruction = SYSTEM_PROMPT
    if summary:
        system_instruction += f"\n\nTóm tắt hội thoại trước đó:\n{summary}"

    # Gemini dùng role "model" cho câu trả lời của assistant.
    contents = [
        types.Content(
            role="model" if message.role == "assistant" else "user",
            parts=[types.Part.from_text(text=message.content)],
        )
        for message in messages
    ]
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=question)])
    )
    return ChatContext(system_instruction=system_instruction, contents=contents)
