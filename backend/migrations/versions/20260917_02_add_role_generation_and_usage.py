"""Bổ sung role, generation, usage và cấu hình quản trị cho v4.2."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260917_02"
down_revision = "20260917_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Migration chỉ thêm mới; user v3 hiện hữu tự nhận role=user.
    op.add_column(
        "users",
        sa.Column("role", sa.String(16), server_default="user", nullable=False),
    )
    op.create_check_constraint("ck_users_role", "users", "role IN ('user', 'admin')")

    op.create_table(
        "generation_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_request_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("requested_model", sa.String(128)),
        sa.Column("actual_model", sa.String(128)),
        sa.Column("user_message_id", sa.Uuid()),
        sa.Column("assistant_message_id", sa.Uuid()),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("queued_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"], ["messages.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "client_request_id", name="uq_generation_user_client"),
    )
    op.create_index(
        "ix_generation_conversation_status",
        "generation_requests",
        ["conversation_id", "status"],
    )
    op.create_index(
        "ix_generation_status_queued", "generation_requests", ["status", "queued_at"]
    )
    op.create_index(
        "uq_generation_active_conversation",
        "generation_requests",
        ["conversation_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('PENDING', 'QUEUED', 'GENERATING', 'RETRYING')"
        ),
    )

    op.create_table(
        "model_usages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generation_request_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("estimated_input_tokens", sa.Integer(), nullable=False),
        sa.Column("actual_input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("provider_status_code", sa.Integer()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_request_id"], ["generation_requests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_usages_generation_request_id",
        "model_usages",
        ["generation_request_id"],
    )

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(96), nullable=False),
        sa.Column("value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("value_type", sa.String(16), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target", sa.String(160), nullable=False),
        sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_logs_admin_id", "admin_audit_logs", ["admin_id"])


def downgrade() -> None:
    op.drop_index("ix_admin_audit_logs_admin_id", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_table("system_settings")
    op.drop_index("ix_model_usages_generation_request_id", table_name="model_usages")
    op.drop_table("model_usages")
    op.drop_index("uq_generation_active_conversation", table_name="generation_requests")
    op.drop_index("ix_generation_status_queued", table_name="generation_requests")
    op.drop_index("ix_generation_conversation_status", table_name="generation_requests")
    op.drop_table("generation_requests")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
