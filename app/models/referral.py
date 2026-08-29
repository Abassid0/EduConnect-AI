import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        Index("idx_referrals_code", "code"),
        Index("idx_referrals_referrer_type", "referrer_type"),
        Index("idx_referrals_parent_id", "parent_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    referrer_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # agent, parent, partner
    referrer_name: Mapped[str | None] = mapped_column(String(150))
    referrer_whatsapp: Mapped[str | None] = mapped_column(String(20))
    referrer_email: Mapped[str | None] = mapped_column(String(200))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parents.id")
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id")
    )
    total_registrations: Mapped[int] = mapped_column(default=0)
    total_revenue: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00")
    )
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00")
    )
    commission_earned: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00")
    )
    commission_status: Mapped[str] = mapped_column(
        String(20), default="unpaid"
    )  # unpaid, pending, paid
    is_active: Mapped[bool] = mapped_column(default=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
