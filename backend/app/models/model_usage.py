from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class ModelUsage(Base):
    __tablename__ = "model_usages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    generation_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("generation_requests.id", ondelete="CASCADE"), index=True
    )
    operation: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(128))
    attempt_number: Mapped[int] = mapped_column(Integer)
    estimated_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    actual_input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    provider_status_code: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    latency_ms: Mapped[int] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
