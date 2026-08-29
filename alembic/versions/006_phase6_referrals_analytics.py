"""Phase 6: referrals and analytics events

Revision ID: 006
Revises: 005
Create Date: 2026-08-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referrals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("referrer_type", sa.String(20), nullable=False),
        sa.Column("referrer_name", sa.String(150)),
        sa.Column("referrer_whatsapp", sa.String(20)),
        sa.Column("referrer_email", sa.String(200)),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("parents.id")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("admin_users.id")),
        sa.Column("total_registrations", sa.Integer, default=0),
        sa.Column("total_revenue", sa.Numeric(14, 2), default=0),
        sa.Column("commission_rate", sa.Numeric(5, 2), default=0),
        sa.Column("commission_earned", sa.Numeric(14, 2), default=0),
        sa.Column("commission_status", sa.String(20), default="unpaid"),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("metadata", JSONB, default={}),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_referrals_code", "referrals", ["code"])
    op.create_index("idx_referrals_referrer_type", "referrals", ["referrer_type"])
    op.create_index("idx_referrals_parent_id", "referrals", ["parent_id"])

    op.create_table(
        "analytics_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("whatsapp_number", sa.String(20)),
        sa.Column("parent_id", UUID(as_uuid=True)),
        sa.Column("student_id", UUID(as_uuid=True)),
        sa.Column("conversation_id", UUID(as_uuid=True)),
        sa.Column("referral_code", sa.String(20)),
        sa.Column("properties", JSONB, default={}),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_analytics_event_type", "analytics_events", ["event_type"])
    op.create_index("idx_analytics_whatsapp", "analytics_events", ["whatsapp_number"])
    op.create_index("idx_analytics_created", "analytics_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("analytics_events")
    op.drop_table("referrals")
