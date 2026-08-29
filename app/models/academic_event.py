import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

EVENT_TYPES = ["term_start", "term_end", "exam_week", "pta", "holiday", "custom"]

EVENT_TYPE_EMOJI = {
    "term_start": "📅",
    "term_end": "📅",
    "exam_week": "📝",
    "pta": "👥",
    "holiday": "🎉",
    "custom": "📌",
}

EVENT_TYPE_LABELS = {
    "term_start": "Term Start",
    "term_end": "Term End",
    "exam_week": "Exam Week",
    "pta": "PTA Meeting",
    "holiday": "Holiday",
    "custom": "Event",
}


class AcademicEvent(Base):
    __tablename__ = "academic_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    school_term: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @property
    def emoji(self) -> str:
        return EVENT_TYPE_EMOJI.get(self.event_type, "📌")

    @property
    def label(self) -> str:
        return EVENT_TYPE_LABELS.get(self.event_type, self.event_type.replace("_", " ").title())

    @property
    def date_display(self) -> str:
        start = self.start_date.strftime("%d %b %Y") if self.start_date else ""
        if self.end_date and self.end_date != self.start_date:
            end = self.end_date.strftime("%d %b %Y")
            return f"{start} – {end}"
        return start
