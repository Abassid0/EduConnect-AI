import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    department: str | None = None
    is_active: bool = True
    last_login_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: str = "support_agent"
    department: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class SupportTicketOut(BaseModel):
    id: uuid.UUID
    ticket_number: str
    conversation_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    department: str
    category: str | None = None
    priority: str
    status: str
    subject: str
    description: str | None = None
    escalation_reason: str | None = None
    whatsapp_number: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SupportTicketListOut(BaseModel):
    id: uuid.UUID
    ticket_number: str
    department: str
    priority: str
    status: str
    subject: str
    assigned_to: uuid.UUID | None = None
    whatsapp_number: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class TicketAssignRequest(BaseModel):
    agent_id: uuid.UUID


class InternalNoteOut(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    conversation_id: uuid.UUID | None = None
    author_id: uuid.UUID
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class InternalNoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4096)
    conversation_id: uuid.UUID | None = None


class ConversationInboxOut(BaseModel):
    id: uuid.UUID
    whatsapp_id: str
    status: str
    current_flow: str | None = None
    assigned_agent_id: uuid.UUID | None = None
    last_message_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SendReplyRequest(BaseModel):
    whatsapp_number: str = Field(min_length=10, max_length=20)
    message: str = Field(min_length=1, max_length=4096)
    msg_type: str = "text"
    template_name: str | None = Field(default=None, max_length=100)
    template_params: list[str] | None = None


class CustomerProfileOut(BaseModel):
    parent: dict
    students: list[dict]
    payments: list[dict]
    tickets: list[dict]
    preferences: dict | None = None
