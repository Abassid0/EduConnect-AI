"""Add category and track columns to programmes

Revision ID: 016
Revises: 015
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "programmes",
        sa.Column("category", sa.String(50), nullable=False, server_default="primary"),
    )
    op.add_column(
        "programmes",
        sa.Column("track", sa.String(50), nullable=True),
    )
    op.create_index("ix_programmes_category", "programmes", ["category"])


def downgrade() -> None:
    op.drop_index("ix_programmes_category", table_name="programmes")
    op.drop_column("programmes", "track")
    op.drop_column("programmes", "category")
