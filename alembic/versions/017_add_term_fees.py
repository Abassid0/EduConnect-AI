"""Add term-based fee structure to programmes

Revision ID: 017
Revises: 016
Create Date: 2026-08-31
"""

from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "programmes",
        sa.Column(
            "fee_structure",
            sa.String(20),
            nullable=False,
            server_default="annual",
        ),
    )
    op.add_column(
        "programmes",
        sa.Column("term_1_fee", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "programmes",
        sa.Column("term_2_fee", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "programmes",
        sa.Column("term_3_fee", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "programmes",
        sa.Column("academic_year", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("programmes", "academic_year")
    op.drop_column("programmes", "term_3_fee")
    op.drop_column("programmes", "term_2_fee")
    op.drop_column("programmes", "term_1_fee")
    op.drop_column("programmes", "fee_structure")
