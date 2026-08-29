import random
import string
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support_ticket import InternalNote, SupportTicket

DEPARTMENTS = [
    "admissions",
    "payments",
    "technical",
    "academic",
    "parent",
    "partnerships",
    "general",
]

KEYWORD_DEPARTMENT_MAP = {
    "register": "admissions",
    "admission": "admissions",
    "enrol": "admissions",
    "enroll": "admissions",
    "application": "admissions",
    "pay": "payments",
    "payment": "payments",
    "fee": "payments",
    "invoice": "payments",
    "refund": "payments",
    "receipt": "payments",
    "billing": "payments",
    "login": "technical",
    "error": "technical",
    "bug": "technical",
    "not working": "technical",
    "app": "technical",
    "class": "academic",
    "schedule": "academic",
    "teacher": "academic",
    "curriculum": "academic",
    "exam": "academic",
    "result": "academic",
    "grade": "academic",
    "child": "parent",
    "student": "parent",
    "pickup": "parent",
    "partner": "partnerships",
    "sponsor": "partnerships",
    "collaborate": "partnerships",
}

PRIORITY_KEYWORDS = {
    "urgent": "high",
    "immediately": "high",
    "emergency": "high",
    "asap": "high",
    "critical": "high",
    "refund": "high",
    "dispute": "high",
}


def generate_ticket_number() -> str:
    digits = "".join(random.choices(string.digits, k=6))
    return f"EDP-{digits}"


def auto_detect_department(text: str) -> str:
    lower = text.lower()
    for keyword, dept in KEYWORD_DEPARTMENT_MAP.items():
        if keyword in lower:
            return dept
    return "general"


def auto_detect_priority(text: str) -> str:
    lower = text.lower()
    for keyword, priority in PRIORITY_KEYWORDS.items():
        if keyword in lower:
            return priority
    return "medium"


async def create_ticket(
    subject: str,
    db: AsyncSession,
    description: str | None = None,
    department: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    conversation_id: uuid.UUID | None = None,
    parent_id: uuid.UUID | None = None,
    whatsapp_number: str | None = None,
    escalation_reason: str | None = None,
    metadata: dict | None = None,
) -> SupportTicket:
    if not department:
        department = auto_detect_department(subject + " " + (description or ""))
    if not priority:
        priority = auto_detect_priority(subject + " " + (description or ""))

    ticket_number = generate_ticket_number()
    existing = await db.execute(
        select(SupportTicket).where(SupportTicket.ticket_number == ticket_number)
    )
    while existing.scalar_one_or_none() is not None:
        ticket_number = generate_ticket_number()
        existing = await db.execute(
            select(SupportTicket).where(SupportTicket.ticket_number == ticket_number)
        )

    ticket = SupportTicket(
        id=uuid.uuid4(),
        ticket_number=ticket_number,
        conversation_id=conversation_id,
        parent_id=parent_id,
        department=department,
        category=category,
        priority=priority,
        status="open",
        subject=subject,
        description=description,
        escalation_reason=escalation_reason,
        whatsapp_number=whatsapp_number,
        metadata_=metadata or {},
    )
    db.add(ticket)
    await db.flush()
    return ticket


async def assign_ticket(
    ticket_id: uuid.UUID,
    agent_id: uuid.UUID,
    db: AsyncSession,
) -> SupportTicket:
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise ValueError("Ticket not found")
    ticket.assigned_to = agent_id
    if ticket.status == "open":
        ticket.status = "in_progress"
    await db.flush()
    await db.refresh(ticket)
    return ticket


async def close_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession,
) -> SupportTicket:
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise ValueError("Ticket not found")
    ticket.status = "closed"
    ticket.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(ticket)
    return ticket


async def get_ticket(
    ticket_id: uuid.UUID, db: AsyncSession
) -> SupportTicket | None:
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    return result.scalar_one_or_none()


async def get_ticket_by_number(
    ticket_number: str, db: AsyncSession
) -> SupportTicket | None:
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.ticket_number == ticket_number)
    )
    return result.scalar_one_or_none()


async def get_tickets(
    db: AsyncSession,
    status: str | None = None,
    department: str | None = None,
    priority: str | None = None,
    assigned_to: uuid.UUID | None = None,
    parent_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SupportTicket]:
    query = select(SupportTicket).order_by(SupportTicket.created_at.desc())
    if status:
        query = query.where(SupportTicket.status == status)
    if department:
        query = query.where(SupportTicket.department == department)
    if priority:
        query = query.where(SupportTicket.priority == priority)
    if assigned_to:
        query = query.where(SupportTicket.assigned_to == assigned_to)
    if parent_id:
        query = query.where(SupportTicket.parent_id == parent_id)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def add_note(
    ticket_id: uuid.UUID,
    author_id: uuid.UUID,
    content: str,
    db: AsyncSession,
    conversation_id: uuid.UUID | None = None,
) -> InternalNote:
    note = InternalNote(
        id=uuid.uuid4(),
        ticket_id=ticket_id,
        conversation_id=conversation_id,
        author_id=author_id,
        content=content,
    )
    db.add(note)
    await db.flush()
    return note


async def get_notes_for_ticket(
    ticket_id: uuid.UUID, db: AsyncSession
) -> list[InternalNote]:
    result = await db.execute(
        select(InternalNote)
        .where(InternalNote.ticket_id == ticket_id)
        .order_by(InternalNote.created_at)
    )
    return list(result.scalars().all())


async def get_ticket_counts_by_status(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(
        select(SupportTicket.status, func.count(SupportTicket.id))
        .group_by(SupportTicket.status)
    )
    return dict(result.all())
