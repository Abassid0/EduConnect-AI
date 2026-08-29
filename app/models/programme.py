import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Programme(Base):
    __tablename__ = "programmes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    age_range_min: Mapped[int | None] = mapped_column(Integer)
    age_range_max: Mapped[int | None] = mapped_column(Integer)
    level: Mapped[str | None] = mapped_column(String(50))
    duration: Mapped[str | None] = mapped_column(String(100))
    delivery_mode: Mapped[str | None] = mapped_column(String(50))
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    available_slots: Mapped[int] = mapped_column(Integer, default=0)
    instructor: Mapped[str | None] = mapped_column(String(150))
    registration_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    schedules: Mapped[list["ClassSchedule"]] = relationship(
        "ClassSchedule", back_populates="programme", lazy="selectin"
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment", back_populates="programme", lazy="selectin"
    )
