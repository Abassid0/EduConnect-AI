import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.services import analytics_service, support_service
from app.services.admin_notify import notify_escalation
from app.services.whatsapp_service import wa_service

logger = logging.getLogger(__name__)

ESCALATION_TRIGGERS = {
    "human_request": {
        "department": "general",
        "priority": "medium",
        "subject_prefix": "Human agent requested",
    },
    "payment_dispute": {
        "department": "payments",
        "priority": "high",
        "subject_prefix": "Payment dispute",
    },
    "refund_request": {
        "department": "payments",
        "priority": "high",
        "subject_prefix": "Refund request",
    },
    "technical_issue": {
        "department": "technical",
        "priority": "medium",
        "subject_prefix": "Unresolved technical issue",
    },
    "low_confidence": {
        "department": "general",
        "priority": "low",
        "subject_prefix": "Low AI confidence",
    },
    "manual_approval": {
        "department": "admissions",
        "priority": "medium",
        "subject_prefix": "Registration requiring approval",
    },
}


async def escalate(
    conversation_id: uuid.UUID,
    whatsapp_number: str,
    reason: str,
    db: AsyncSession,
    description: str | None = None,
    parent_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> support_service.SupportTicket:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise ValueError("Conversation not found")

    conversation.status = "paused_for_agent"

    trigger = ESCALATION_TRIGGERS.get(reason, ESCALATION_TRIGGERS["human_request"])
    subject = f"{trigger['subject_prefix']} — {whatsapp_number}"

    ticket = await support_service.create_ticket(
        subject=subject,
        db=db,
        description=description,
        department=trigger["department"],
        priority=trigger["priority"],
        conversation_id=conversation_id,
        parent_id=parent_id,
        whatsapp_number=whatsapp_number,
        escalation_reason=reason,
        metadata=metadata,
    )

    await analytics_service.track_event(
        "support_escalation",
        db,
        whatsapp_number=whatsapp_number,
        conversation_id=conversation_id,
        properties={
            "reason": reason,
            "department": trigger["department"],
            "ticket_number": ticket.ticket_number,
        },
    )

    await notify_escalation(
        ticket_number=ticket.ticket_number,
        department=trigger["department"],
        priority=trigger["priority"],
        reason=reason,
        user_id=whatsapp_number,
    )

    try:
        await wa_service.send_text(
            whatsapp_number,
            f"Your request has been escalated to our support team.\n\n"
            f"Ticket: *{ticket.ticket_number}*\n"
            f"A team member will reach out to you shortly.\n\n"
            f"Thank you for your patience.",
        )
    except Exception:
        logger.exception("Failed to send escalation confirmation to %s", whatsapp_number)

    await db.flush()
    return ticket


async def resume_bot(
    conversation_id: uuid.UUID,
    db: AsyncSession,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise ValueError("Conversation not found")

    conversation.status = "active"
    conversation.current_flow = None
    conversation.current_step = None
    conversation.flow_data = {}
    conversation.assigned_agent_id = None
    await db.flush()
    await db.refresh(conversation)

    try:
        await wa_service.send_text(
            conversation.whatsapp_id,
            "Your conversation with our support team has ended.\n"
            "The bot is back online — reply *menu* anytime to continue.",
        )
    except Exception:
        logger.exception(
            "Failed to send resume notification to %s", conversation.whatsapp_id
        )

    return conversation


async def pause_conversation(
    conversation_id: uuid.UUID,
    agent_id: uuid.UUID | None,
    db: AsyncSession,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise ValueError("Conversation not found")

    conversation.status = "paused_for_agent"
    if agent_id:
        conversation.assigned_agent_id = agent_id
    await db.flush()
    await db.refresh(conversation)
    return conversation
