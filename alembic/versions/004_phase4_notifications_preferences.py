"""Phase 4: notification preferences and notifications

Revision ID: 004
Revises: 003
Create Date: 2026-08-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("parents.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "class_reminders",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "payment_reminders",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "marketing",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "events",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "progress_reports",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
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

    op.create_table(
        "notifications",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True
        ),
        sa.Column(
            "recipient_whatsapp", sa.String(20), nullable=False
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("parents.id"),
            nullable=True,
        ),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("students.id"),
            nullable=True,
        ),
        sa.Column(
            "notification_type", sa.String(50), nullable=False
        ),
        sa.Column("event_key", sa.String(200), nullable=True),
        sa.Column("template_name", sa.String(100), nullable=True),
        sa.Column("message_body", sa.Text, nullable=True),
        sa.Column(
            "channel",
            sa.String(20),
            server_default=sa.text("'whatsapp'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "scheduled_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "sent_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "retry_count",
            sa.Integer,
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            server_default=sa.text("'{}'"),
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
        "idx_notifications_recipient",
        "notifications",
        ["recipient_whatsapp"],
    )
    op.create_index(
        "idx_notifications_type_event",
        "notifications",
        ["notification_type", "event_key"],
    )
    op.create_index(
        "idx_notifications_status", "notifications", ["status"]
    )
    op.create_index(
        "idx_notifications_scheduled", "notifications", ["scheduled_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_notifications_scheduled", table_name="notifications")
    op.drop_index("idx_notifications_status", table_name="notifications")
    op.drop_index("idx_notifications_type_event", table_name="notifications")
    op.drop_index("idx_notifications_recipient", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("notification_preferences")
