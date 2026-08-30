"""Widen sender and recipient columns on messages

Revision ID: 015
Revises: 014
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "messages", "sender",
        type_=sa.String(100),
        existing_type=sa.String(20),
        existing_nullable=False,
    )
    op.alter_column(
        "messages", "recipient",
        type_=sa.String(100),
        existing_type=sa.String(20),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "messages", "sender",
        type_=sa.String(20),
        existing_type=sa.String(100),
        existing_nullable=False,
    )
    op.alter_column(
        "messages", "recipient",
        type_=sa.String(20),
        existing_type=sa.String(100),
        existing_nullable=False,
    )
