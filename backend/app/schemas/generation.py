from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


GenerationStatus = Literal[
    "PENDING", "QUEUED", "GENERATING", "RETRYING", "DONE", "FAILED", "CANCELLED"
]


class ChatJobRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    conversation_id: UUID
    message: str = Field(min_length=1)
    client_request_id: UUID
    model: Literal["default", "advanced"] = "default"

    @field_validator("message")
    @classmethod
    def reject_local_command(cls, value: str) -> str:
        if value.startswith("/"):
            raise ValueError("Lệnh chat phải được xử lý cục bộ, không gửi tới model")
        return value


class GenerationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: UUID = Field(validation_alias="id")
    conversation_id: UUID
    status: GenerationStatus
    queue_position: int | None = None
    requested_model: str | None = None
    actual_model: str | None = None
    attempt_count: int
    error_code: str | None = None
    error_message: str | None = None
    user_message_id: UUID | None = None
    assistant_message_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class ChatJobAccepted(BaseModel):
    request_id: UUID
    status: GenerationStatus
    queue_position: int | None
