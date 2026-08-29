"""Phase 2: parents, students, programmes, class_schedules, enrollments

Revision ID: 002
Revises: 001
Create Date: 2026-08-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("whatsapp_number", sa.String(20), unique=True, nullable=False),
        sa.Column("full_name", sa.String(150), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("alt_phone", sa.String(20), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column(
            "consent_given",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("consent_date", sa.DateTime(timezone=True), nullable=True),
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
        "programmes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("age_range_min", sa.Integer, nullable=True),
        sa.Column("age_range_max", sa.Integer, nullable=True),
        sa.Column("level", sa.String(50), nullable=True),
        sa.Column("duration", sa.String(100), nullable=True),
        sa.Column("delivery_mode", sa.String(50), nullable=True),
        sa.Column("fee", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "currency",
            sa.String(3),
            server_default=sa.text("'NGN'"),
            nullable=False,
        ),
        sa.Column(
            "available_slots",
            sa.Integer,
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("instructor", sa.String(150), nullable=True),
        sa.Column("registration_url", sa.String(500), nullable=True),
        sa.Column(
            "is_active",
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
    )

    op.create_table(
        "students",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("parents.id"),
            nullable=False,
        ),
        sa.Column("registration_id", sa.String(20), unique=True, nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("age", sa.Integer, nullable=True),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("emergency_contact_name", sa.String(150), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(20), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'registered'"),
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
        "class_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "programme_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("programmes.id"),
            nullable=False,
        ),
        sa.Column("day_of_week", sa.Integer, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column(
            "timezone",
            sa.String(50),
            server_default=sa.text("'Africa/Lagos'"),
            nullable=False,
        ),
    )

    op.create_table(
        "enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("students.id"),
            nullable=False,
        ),
        sa.Column(
            "programme_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("programmes.id"),
            nullable=False,
        ),
        sa.Column(
            "schedule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("class_schedules.id"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("enrollments")
    op.drop_table("class_schedules")
    op.drop_table("students")
    op.drop_table("programmes")
    op.drop_table("parents")
