"""Phase 6B: AI interactions log table

Revision ID: 007
Revises: 006
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_interactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("parents.id"), nullable=True),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("tools_called", JSONB, server_default="[]"),
        sa.Column("ai_response", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("escalated", sa.Boolean(), server_default="false"),
        sa.Column("response_time_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ai_interactions_conversation", "ai_interactions", ["conversation_id"])
    op.create_index("idx_ai_interactions_created", "ai_interactions", ["created_at"])
    op.create_index("idx_ai_interactions_escalated", "ai_interactions", ["escalated"])


def downgrade() -> None:
    op.drop_index("idx_ai_interactions_escalated")
    op.drop_index("idx_ai_interactions_created")
    op.drop_index("idx_ai_interactions_conversation")
    op.drop_table("ai_interactions")
