import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


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
    full_name: str
    password: str
    role: str = "support_agent"
    department: str | None = None


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
    content: str
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
    whatsapp_number: str
    message: str
    msg_type: str = "text"
    template_name: str | None = None
    template_params: list[str] | None = None


class CustomerProfileOut(BaseModel):
    parent: dict
    students: list[dict]
    payments: list[dict]
    tickets: list[dict]
    preferences: dict | None = None
