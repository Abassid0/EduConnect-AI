"""Phase 9: Academic Calendar — academic_events table.

Revision ID: 009
Revises: 008
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "academic_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False, server_default="custom"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("school_term", sa.String(100), nullable=True),
        sa.Column("is_published", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_academic_events_start_date", "academic_events", ["start_date"]
    )
    op.create_index(
        "ix_academic_events_event_type", "academic_events", ["event_type"]
    )
    op.create_index(
        "ix_academic_events_is_published", "academic_events", ["is_published"]
    )


def downgrade() -> None:
    op.drop_index("ix_academic_events_is_published", table_name="academic_events")
    op.drop_index("ix_academic_events_event_type", table_name="academic_events")
    op.drop_index("ix_academic_events_start_date", table_name="academic_events")
    op.drop_table("academic_events")
