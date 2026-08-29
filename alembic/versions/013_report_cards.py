"""Phase E: Report Cards — report_cards, report_card_subjects, report_card_deliveries.

Revision ID: 013
Revises: 012
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_cards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "student_id",
            UUID(as_uuid=True),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("academic_term", sa.String(100), nullable=False),
        sa.Column("overall_grade", sa.String(10), nullable=True),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("position_in_class", sa.Integer, nullable=True),
        sa.Column("class_size", sa.Integer, nullable=True),
        sa.Column("teacher_comment", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "published_by",
            UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("student_id", "academic_term", name="uq_student_term"),
    )

    op.create_table(
        "report_card_subjects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_card_id",
            UUID(as_uuid=True),
            sa.ForeignKey("report_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject_name", sa.String(100), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("grade", sa.String(10), nullable=True),
        sa.Column("teacher_comment", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "report_card_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_card_id",
            UUID(as_uuid=True),
            sa.ForeignKey("report_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("parents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_via", sa.String(20), nullable=True),
        sa.UniqueConstraint("report_card_id", "parent_id", name="uq_rc_parent"),
    )


def downgrade() -> None:
    op.drop_table("report_card_deliveries")
    op.drop_table("report_card_subjects")
    op.drop_table("report_cards")
