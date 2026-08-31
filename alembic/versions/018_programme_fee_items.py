"""Programme fee items – itemized fee breakdown per programme/term

Revision ID: 018
Revises: 017
Create Date: 2026-08-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "programme_fee_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "programme_id",
            UUID(as_uuid=True),
            sa.ForeignKey("programmes.id"),
            nullable=False,
        ),
        sa.Column(
            "fee_type_id",
            UUID(as_uuid=True),
            sa.ForeignKey("fee_types.id"),
            nullable=False,
        ),
        sa.Column("term", sa.String(20), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_optional", sa.Boolean, server_default="false"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_pfi_programme", "programme_fee_items", ["programme_id"])
    op.create_index("idx_pfi_fee_type", "programme_fee_items", ["fee_type_id"])
    op.create_index(
        "uq_pfi_programme_fee_term",
        "programme_fee_items",
        ["programme_id", "fee_type_id", "term"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_pfi_programme_fee_term", table_name="programme_fee_items")
    op.drop_index("idx_pfi_fee_type", table_name="programme_fee_items")
    op.drop_index("idx_pfi_programme", table_name="programme_fee_items")
    op.drop_table("programme_fee_items")
