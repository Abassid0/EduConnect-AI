import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReportCard(Base):
    __tablename__ = "report_cards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    academic_term: Mapped[str] = mapped_column(String(100), nullable=False)
    overall_grade: Mapped[str | None] = mapped_column(String(10))
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    position_in_class: Mapped[int | None] = mapped_column(Integer)
    class_size: Mapped[int | None] = mapped_column(Integer)
    teacher_comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    subjects: Mapped[list["ReportCardSubject"]] = relationship(
        "ReportCardSubject",
        back_populates="report_card",
        lazy="selectin",
        order_by="ReportCardSubject.sort_order, ReportCardSubject.subject_name",
        cascade="all, delete-orphan",
    )
    deliveries: Mapped[list["ReportCardDelivery"]] = relationship(
        "ReportCardDelivery",
        back_populates="report_card",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("student_id", "academic_term", name="uq_student_term"),
    )


class ReportCardSubject(Base):
    __tablename__ = "report_card_subjects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_cards.id", ondelete="CASCADE"), nullable=False
    )
    subject_name: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    grade: Mapped[str | None] = mapped_column(String(10))
    teacher_comment: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    report_card: Mapped["ReportCard"] = relationship("ReportCard", back_populates="subjects")


class ReportCardDelivery(Base):
    __tablename__ = "report_card_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_cards.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parents.id", ondelete="CASCADE"), nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_via: Mapped[str | None] = mapped_column(String(20))

    report_card: Mapped["ReportCard"] = relationship("ReportCard", back_populates="deliveries")

    __table_args__ = (
        UniqueConstraint("report_card_id", "parent_id", name="uq_rc_parent"),
    )
