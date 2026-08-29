import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

SLIP_STATUSES = ["draft", "active", "closed"]
RESPONSE_VALUES = ["yes", "no", "pending"]
RESPONSE_VIA = ["whatsapp", "admin"]


class PermissionSlip(Base):
    __tablename__ = "permission_slips"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    segment_type: Mapped[str] = mapped_column(String(30), nullable=False, default="all")
    segment_value: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    responses: Mapped[list["PermissionSlipResponse"]] = relationship(
        "PermissionSlipResponse", back_populates="slip", lazy="selectin"
    )


class PermissionSlipResponse(Base):
    __tablename__ = "permission_slip_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permission_slips.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parents.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    response: Mapped[str] = mapped_column(String(10), nullable=False, default="pending")
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_via: Mapped[str | None] = mapped_column(String(20))

    slip: Mapped["PermissionSlip"] = relationship("PermissionSlip", back_populates="responses")

    __table_args__ = (
        UniqueConstraint("slip_id", "parent_id", name="uq_slip_parent"),
    )
