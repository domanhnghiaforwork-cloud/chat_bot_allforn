from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


ACTIVE_GENERATION_STATUSES = ("PENDING", "QUEUED", "GENERATING", "RETRYING")
TERMINAL_GENERATION_STATUSES = ("DONE", "FAILED", "CANCELLED")


class GenerationRequest(Base):
    __tablename__ = "generation_requests"
    __table_args__ = (
        UniqueConstraint("user_id", "client_request_id", name="uq_generation_user_client"),
        Index("ix_generation_conversation_status", "conversation_id", "status"),
        Index("ix_generation_status_queued", "status", "queued_at"),
        # PostgreSQL là lớp chặn cuối cùng cho single-flight theo conversation.
        Index(
            "uq_generation_active_conversation",
            "conversation_id",
            unique=True,
            postgresql_where=text(
                "status IN ('PENDING', 'QUEUED', 'GENERATING', 'RETRYING')"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_request_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    question: Mapped[str] = mapped_column(Text)
    operation: Mapped[str] = mapped_column(String(32), default="chat")
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    requested_model: Mapped[str | None] = mapped_column(String(128))
    actual_model: Mapped[str | None] = mapped_column(String(128))
    user_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    assistant_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
