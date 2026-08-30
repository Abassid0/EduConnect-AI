import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, model_validator

from app.models.programme import (
    CATEGORY_LEVELS,
    PROGRAMME_CATEGORIES,
    SSS_LEVELS,
    TRACKS,
)


class ProgrammeOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    category: str
    age_range_min: int | None = None
    age_range_max: int | None = None
    level: str | None = None
    track: str | None = None
    duration: str | None = None
    delivery_mode: str | None = None
    fee: Decimal
    currency: str = "NGN"
    available_slots: int = 0
    instructor: str | None = None
    is_active: bool = True

    class Config:
        from_attributes = True


class ProgrammeCreate(BaseModel):
    name: str
    description: str | None = None
    category: str
    age_range_min: int | None = None
    age_range_max: int | None = None
    level: str | None = None
    track: str | None = None
    duration: str | None = None
    delivery_mode: str | None = None
    fee: Decimal
    currency: str = "NGN"
    available_slots: int = 0
    instructor: str | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_category_level_track(self):
        if self.category not in PROGRAMME_CATEGORIES:
            raise ValueError(f"category must be one of {PROGRAMME_CATEGORIES}")
        if self.level:
            valid_levels = CATEGORY_LEVELS.get(self.category, ())
            if self.level not in valid_levels:
                raise ValueError(
                    f"level '{self.level}' is not valid for category '{self.category}'"
                )
        if self.track:
            if self.track not in TRACKS:
                raise ValueError(f"track must be one of {TRACKS}")
            if self.level not in SSS_LEVELS:
                raise ValueError(
                    "track is only applicable to SSS levels (sss_1, sss_2, sss_3)"
                )
        return self


class ProgrammeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    age_range_min: int | None = None
    age_range_max: int | None = None
    level: str | None = None
    track: str | None = None
    duration: str | None = None
    delivery_mode: str | None = None
    fee: Decimal | None = None
    available_slots: int | None = None
    instructor: str | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_category_level_track(self):
        if self.category is not None and self.category not in PROGRAMME_CATEGORIES:
            raise ValueError(f"category must be one of {PROGRAMME_CATEGORIES}")
        if self.level is not None and self.category is not None:
            valid_levels = CATEGORY_LEVELS.get(self.category, ())
            if self.level not in valid_levels:
                raise ValueError(
                    f"level '{self.level}' is not valid for category '{self.category}'"
                )
        if self.track is not None:
            if self.track not in TRACKS:
                raise ValueError(f"track must be one of {TRACKS}")
        return self


class ScheduleOut(BaseModel):
    id: uuid.UUID
    programme_id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    timezone: str = "Africa/Lagos"

    class Config:
        from_attributes = True


class ScheduleCreate(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time
    timezone: str = "Africa/Lagos"


class ParentOut(BaseModel):
    id: uuid.UUID
    whatsapp_number: str
    full_name: str | None = None
    email: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class StudentOut(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID
    registration_id: str
    full_name: str
    date_of_birth: date | None = None
    age: int | None = None
    gender: str | None = None
    status: str = "registered"
    created_at: datetime

    class Config:
        from_attributes = True


class EnrollmentOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    programme_id: uuid.UUID
    schedule_id: uuid.UUID | None = None
    status: str = "pending"
    enrolled_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True
