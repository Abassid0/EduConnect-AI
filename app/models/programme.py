import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base

PROGRAMME_CATEGORIES = ("pre_primary", "primary", "secondary")
FEE_STRUCTURES = ("annual", "per_term")
TERMS = ("first", "second", "third")
TERM_LABELS = {"first": "1st Term", "second": "2nd Term", "third": "3rd Term"}

CATEGORY_LEVELS = {
    "pre_primary": ("nursery_1", "nursery_2", "kg_1", "kg_2"),
    "primary": ("primary_1", "primary_2", "primary_3", "primary_4", "primary_5", "primary_6"),
    "secondary": ("jss_1", "jss_2", "jss_3", "sss_1", "sss_2", "sss_3"),
}

SSS_LEVELS = ("sss_1", "sss_2", "sss_3")
TRACKS = ("science", "commercial", "arts")

ALL_LEVELS = tuple(lvl for levels in CATEGORY_LEVELS.values() for lvl in levels)

CATEGORY_LABELS = {
    "pre_primary": "Pre-Primary",
    "primary": "Primary",
    "secondary": "Secondary",
}

LEVEL_LABELS = {
    "nursery_1": "Nursery 1", "nursery_2": "Nursery 2",
    "kg_1": "KG 1", "kg_2": "KG 2",
    "primary_1": "Primary 1", "primary_2": "Primary 2", "primary_3": "Primary 3",
    "primary_4": "Primary 4", "primary_5": "Primary 5", "primary_6": "Primary 6",
    "jss_1": "JSS 1", "jss_2": "JSS 2", "jss_3": "JSS 3",
    "sss_1": "SSS 1", "sss_2": "SSS 2", "sss_3": "SSS 3",
}

TRACK_LABELS = {
    "science": "Science",
    "commercial": "Commercial",
    "arts": "Arts",
}


class Programme(Base):
    __tablename__ = "programmes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    age_range_min: Mapped[int | None] = mapped_column(Integer)
    age_range_max: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="primary"
    )
    level: Mapped[str | None] = mapped_column(String(50))
    track: Mapped[str | None] = mapped_column(String(50))
    duration: Mapped[str | None] = mapped_column(String(100))
    delivery_mode: Mapped[str | None] = mapped_column(String(50))
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    available_slots: Mapped[int] = mapped_column(Integer, default=0)
    instructor: Mapped[str | None] = mapped_column(String(150))
    registration_url: Mapped[str | None] = mapped_column(String(500))
    fee_structure: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="annual"
    )
    term_1_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    term_2_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    term_3_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    academic_year: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @validates("category")
    def validate_category(self, _key: str, value: str) -> str:
        if value not in PROGRAMME_CATEGORIES:
            raise ValueError(f"Invalid category: {value}")
        return value

    @validates("track")
    def validate_track(self, _key: str, value: str | None) -> str | None:
        if value is not None and value not in TRACKS:
            raise ValueError(f"Invalid track: {value}")
        return value

    @validates("fee_structure")
    def validate_fee_structure(self, _key: str, value: str) -> str:
        if value not in FEE_STRUCTURES:
            raise ValueError(f"Invalid fee_structure: {value}")
        return value

    fee_items: Mapped[list["ProgrammeFeeItem"]] = relationship(
        "ProgrammeFeeItem", back_populates="programme", lazy="selectin"
    )
    schedules: Mapped[list["ClassSchedule"]] = relationship(
        "ClassSchedule", back_populates="programme", lazy="selectin"
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment", back_populates="programme", lazy="selectin"
    )
