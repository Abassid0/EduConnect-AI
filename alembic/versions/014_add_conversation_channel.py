"""Add channel column to conversations

Revision ID: 014
Revises: 013
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("channel", sa.String(20), server_default="whatsapp", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("conversations", "channel")
