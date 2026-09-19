from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationResponse):
    messages: list[MessageResponse]


class ConversationTokenUsage(BaseModel):
    current_tokens: int
    max_conversation_tokens: int
    remaining_tokens: int
    utilization_percent: float
    chat_context_window_tokens: int
    max_chat_input_tokens: int
    max_chat_output_tokens: int
    estimated: bool = True
