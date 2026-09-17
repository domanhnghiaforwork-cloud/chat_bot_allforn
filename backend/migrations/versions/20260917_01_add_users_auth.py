"""Thêm user, auth và quyền sở hữu hội thoại."""

import os
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from pwdlib import PasswordHash

revision = "20260917_01"
down_revision = None
branch_labels = None
depends_on = None


def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def _create_v3_tables() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_conversations_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_table(
        "conversation_summaries",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summarized_message_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("conversation_id"),
    )


def _upgrade_v2_conversations() -> None:
    connection = op.get_bind()
    conversation_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM conversations")
    ).scalar_one()
    owner_id = None

    if conversation_count:
        email = os.getenv("V2_OWNER_EMAIL", "").strip().lower()
        password = os.getenv("V2_OWNER_PASSWORD", "")
        if not email or len(password) < 8:
            raise RuntimeError(
                "Database có hội thoại v2: cần V2_OWNER_EMAIL và "
                "V2_OWNER_PASSWORD (tối thiểu 8 ký tự) để nhận dữ liệu cũ"
            )
        owner_id = uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO users (id, email, password_hash, created_at) "
                "VALUES (:id, :email, :password_hash, CURRENT_TIMESTAMP)"
            ),
            {
                "id": owner_id,
                "email": email,
                "password_hash": PasswordHash.recommended().hash(password),
            },
        )

    op.add_column("conversations", sa.Column("user_id", sa.Uuid(), nullable=True))
    if owner_id:
        connection.execute(
            sa.text("UPDATE conversations SET user_id = :user_id"),
            {"user_id": owner_id},
        )
    op.alter_column("conversations", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_conversations_user_id_users",
        "conversations",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])


def upgrade() -> None:
    # Một revision hỗ trợ cả database mới và database đã chạy v2.
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "users" not in tables:
        _create_users()
    if "conversations" not in tables:
        _create_v3_tables()
    else:
        _upgrade_v2_conversations()


def downgrade() -> None:
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_user_id_users",
        "conversations",
        type_="foreignkey",
    )
    op.drop_column("conversations", "user_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
