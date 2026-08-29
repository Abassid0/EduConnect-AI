"""Phase 3: payments and billing

Revision ID: 003
Revises: 002
Create Date: 2026-08-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True
        ),
        sa.Column(
            "reference", sa.String(50), unique=True, nullable=False
        ),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("students.id"),
            nullable=False,
        ),
        sa.Column(
            "enrollment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enrollments.id"),
            nullable=False,
        ),
        sa.Column(
            "programme_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("programmes.id"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "currency",
            sa.String(3),
            server_default=sa.text("'NGN'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("whatsapp_number", sa.String(20), nullable=False),
        sa.Column("paystack_reference", sa.String(100), nullable=True),
        sa.Column(
            "paystack_authorization_url", sa.String(500), nullable=True
        ),
        sa.Column(
            "paid_at", sa.DateTime(timezone=True), nullable=True
        ),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_payments_reference", "payments", ["reference"])
    op.create_index("idx_payments_student", "payments", ["student_id"])
    op.create_index("idx_payments_status", "payments", ["status"])


def downgrade() -> None:
    op.drop_index("idx_payments_status", table_name="payments")
    op.drop_index("idx_payments_student", table_name="payments")
    op.drop_index("idx_payments_reference", table_name="payments")
    op.drop_table("payments")
