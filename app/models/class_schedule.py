import uuid
from time import struct_time

from sqlalchemy import ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class ClassSchedule(Base):
    __tablename__ = "class_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    programme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programmes.id"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[struct_time] = mapped_column(Time, nullable=False)
    end_time: Mapped[struct_time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Africa/Lagos")

    programme: Mapped["Programme"] = relationship(
        "Programme", back_populates="schedules"
    )

    @property
    def day_name(self) -> str:
        if 0 <= self.day_of_week <= 6:
            return DAY_NAMES[self.day_of_week]
        return str(self.day_of_week)

    @property
    def display(self) -> str:
        start = self.start_time.strftime("%I:%M %p") if self.start_time else ""
        end = self.end_time.strftime("%I:%M %p") if self.end_time else ""
        return f"{self.day_name} {start} - {end}"
