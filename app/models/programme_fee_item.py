import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base
from app.models.programme import TERMS


class ProgrammeFeeItem(Base):
    __tablename__ = "programme_fee_items"
    __table_args__ = (
        Index("idx_pfi_programme", "programme_id"),
        Index("idx_pfi_fee_type", "fee_type_id"),
        Index(
            "uq_pfi_programme_fee_term",
            "programme_id",
            "fee_type_id",
            "term",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    programme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programmes.id"), nullable=False
    )
    fee_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fee_types.id"), nullable=False
    )
    term: Mapped[str | None] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @validates("term")
    def validate_term(self, _key: str, value: str | None) -> str | None:
        if value is not None and value not in TERMS:
            raise ValueError(f"Invalid term: {value}")
        return value

    programme: Mapped["Programme"] = relationship("Programme", back_populates="fee_items")
    fee_type: Mapped["FeeType"] = relationship("FeeType", lazy="selectin")
