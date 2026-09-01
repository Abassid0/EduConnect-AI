import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.academic_event import EVENT_TYPES


class AcademicEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    event_type: str = "custom"
    start_date: date
    end_date: date | None = None
    description: str | None = Field(default=None, max_length=2000)
    school_term: str | None = Field(default=None, max_length=50)
    is_published: bool = True

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("event_type")
    @classmethod
    def valid_event_type(cls, v: str) -> str:
        if v not in EVENT_TYPES:
            raise ValueError(f"event_type must be one of: {', '.join(EVENT_TYPES)}")
        return v


class AcademicEventUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    event_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = Field(default=None, max_length=2000)
    school_term: str | None = Field(default=None, max_length=50)
    is_published: bool | None = None


class AcademicEventOut(BaseModel):
    id: uuid.UUID
    title: str
    event_type: str
    start_date: date
    end_date: date | None
    description: str | None
    school_term: str | None
    is_published: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
