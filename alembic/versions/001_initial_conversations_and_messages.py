"""Initial conversations and messages tables

Revision ID: 001
Revises:
Create Date: 2026-08-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("whatsapp_id", sa.String(20), nullable=False),
        sa.Column("current_flow", sa.String(50), nullable=True),
        sa.Column("current_step", sa.String(50), nullable=True),
        sa.Column(
            "flow_data",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("selected_student_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status", sa.String(20), server_default=sa.text("'active'"), nullable=False
        ),
        sa.Column("assigned_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_conversations_whatsapp", "conversations", ["whatsapp_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("whatsapp_msg_id", sa.String(100), nullable=True),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("msg_type", sa.String(20), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("sender", sa.String(20), nullable=False),
        sa.Column("recipient", sa.String(20), nullable=False),
        sa.Column(
            "delivery_status",
            sa.String(20),
            server_default=sa.text("'sent'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_messages_conversation",
        "messages",
        ["conversation_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_messages_conversation", table_name="messages")
    op.drop_table("messages")
    op.drop_index("idx_conversations_whatsapp", table_name="conversations")
    op.drop_table("conversations")
