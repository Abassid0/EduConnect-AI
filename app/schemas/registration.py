import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.programme import (
    CATEGORY_LEVELS,
    FEE_STRUCTURES,
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
    fee_structure: str = "annual"
    term_1_fee: Decimal | None = None
    term_2_fee: Decimal | None = None
    term_3_fee: Decimal | None = None
    academic_year: str | None = None
    currency: str = "NGN"
    available_slots: int = 0
    instructor: str | None = None
    is_active: bool = True

    class Config:
        from_attributes = True


class ProgrammeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str
    age_range_min: int | None = None
    age_range_max: int | None = None
    level: str | None = None
    track: str | None = None
    duration: str | None = Field(default=None, max_length=100)
    delivery_mode: str | None = Field(default=None, max_length=50)
    fee: Decimal
    fee_structure: str = "annual"
    term_1_fee: Decimal | None = None
    term_2_fee: Decimal | None = None
    term_3_fee: Decimal | None = None
    academic_year: str | None = Field(default=None, max_length=20)
    currency: str = "NGN"
    available_slots: int = 0
    instructor: str | None = Field(default=None, max_length=200)
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
        if self.fee_structure not in FEE_STRUCTURES:
            raise ValueError(f"fee_structure must be one of {FEE_STRUCTURES}")
        if self.fee_structure == "per_term":
            if not all([self.term_1_fee, self.term_2_fee, self.term_3_fee]):
                raise ValueError(
                    "term_1_fee, term_2_fee, and term_3_fee are required "
                    "when fee_structure is 'per_term'"
                )
        return self


class ProgrammeUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = None
    age_range_min: int | None = None
    age_range_max: int | None = None
    level: str | None = None
    track: str | None = None
    duration: str | None = Field(default=None, max_length=100)
    delivery_mode: str | None = Field(default=None, max_length=50)
    fee: Decimal | None = None
    fee_structure: str | None = None
    term_1_fee: Decimal | None = None
    term_2_fee: Decimal | None = None
    term_3_fee: Decimal | None = None
    academic_year: str | None = Field(default=None, max_length=20)
    available_slots: int | None = None
    instructor: str | None = Field(default=None, max_length=200)
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
        if self.fee_structure is not None and self.fee_structure not in FEE_STRUCTURES:
            raise ValueError(f"fee_structure must be one of {FEE_STRUCTURES}")
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
