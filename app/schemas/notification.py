import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationPreferenceOut(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID
    class_reminders: bool = True
    payment_reminders: bool = True
    marketing: bool = False
    events: bool = True
    progress_reports: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationPreferenceUpdate(BaseModel):
    class_reminders: bool | None = None
    payment_reminders: bool | None = None
    marketing: bool | None = None
    events: bool | None = None
    progress_reports: bool | None = None


class NotificationOut(BaseModel):
    id: uuid.UUID
    recipient_whatsapp: str
    parent_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None
    notification_type: str
    event_key: str | None = None
    template_name: str | None = None
    message_body: str | None = None
    channel: str = "whatsapp"
    status: str = "pending"
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    retry_count: int = 0
    error_message: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListOut(BaseModel):
    id: uuid.UUID
    recipient_whatsapp: str
    notification_type: str
    status: str
    sent_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True
