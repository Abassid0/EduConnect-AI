import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.admin import (
    AdminUserOut,
    ConversationInboxOut,
    CustomerProfileOut,
    InternalNoteCreate,
    InternalNoteOut,
    SendReplyRequest,
    SupportTicketListOut,
    SupportTicketOut,
    TicketAssignRequest,
)
from app.services import (
    escalation_service,
    notification_service,
    payment_service,
    registration_service,
    support_service,
)
from app.services.admin_notify import notify_ticket_assigned
from app.services.conversation_engine import log_message
from app.services import messaging
from app.services.messaging import CHANNEL_WHATSAPP
from app.services.whatsapp_service import wa_service
from app.utils.auth import get_current_user, require_role

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Auth: current user ---

@router.get("/me", response_model=AdminUserOut)
async def admin_me(
    current_user: AdminUser = Depends(get_current_user),
) -> AdminUserOut:
    return AdminUserOut.model_validate(current_user)


# --- Conversation Inbox ---

@router.get("/inbox", response_model=list[ConversationInboxOut])
async def conversation_inbox(
    status: str | None = None,
    department: str | None = None,
    priority: str | None = None,
    assigned_to_me: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationInboxOut]:
    query = select(Conversation).order_by(Conversation.last_message_at.desc().nullslast())

    if status:
        query = query.where(Conversation.status == status)
    if assigned_to_me:
        query = query.where(Conversation.assigned_agent_id == current_user.id)

    if department or priority:
        from app.models.support_ticket import SupportTicket
        query = query.join(
            SupportTicket, SupportTicket.conversation_id == Conversation.id
        )
        if department:
            query = query.where(SupportTicket.department == department)
        if priority:
            query = query.where(SupportTicket.priority == priority)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    convos = list(result.scalars().all())
    return [ConversationInboxOut.model_validate(c) for c in convos]


# --- Customer Profile ---

@router.get("/customer/{whatsapp_number}", response_model=CustomerProfileOut)
async def customer_profile(
    whatsapp_number: str,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerProfileOut:
    parent = await registration_service.get_parent_by_whatsapp(whatsapp_number, db)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    students = await registration_service.get_students_for_parent(parent.id, db)
    student_dicts = []
    for s in students:
        enrollments = await registration_service.get_enrollments_for_student(s.id, db)
        student_dicts.append({
            "id": str(s.id),
            "registration_id": s.registration_id,
            "full_name": s.full_name,
            "age": s.age,
            "status": s.status,
            "enrollments": [
                {
                    "id": str(e.id),
                    "programme_id": str(e.programme_id),
                    "status": e.status,
                    "enrolled_at": e.enrolled_at.isoformat() if e.enrolled_at else None,
                }
                for e in enrollments
            ],
        })

    payments = await payment_service.get_payments_for_student_list(
        [s.id for s in students], db
    )
    payment_dicts = [
        {
            "id": str(p.id),
            "reference": p.reference,
            "amount": str(p.amount),
            "status": p.status,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        }
        for p in payments
    ]

    tickets = await support_service.get_tickets(db, parent_id=parent.id, limit=20)
    ticket_dicts = [
        {
            "id": str(t.id),
            "ticket_number": t.ticket_number,
            "subject": t.subject,
            "status": t.status,
            "department": t.department,
            "priority": t.priority,
            "created_at": t.created_at.isoformat(),
        }
        for t in tickets
    ]

    prefs = await notification_service.get_preferences(parent.id, db)
    prefs_dict = None
    if prefs:
        prefs_dict = {
            "class_reminders": prefs.class_reminders,
            "payment_reminders": prefs.payment_reminders,
            "marketing": prefs.marketing,
            "events": prefs.events,
            "progress_reports": prefs.progress_reports,
        }

    return CustomerProfileOut(
        parent={
            "id": str(parent.id),
            "whatsapp_number": parent.whatsapp_number,
            "full_name": parent.full_name,
            "email": parent.email,
            "created_at": parent.created_at.isoformat(),
        },
        students=student_dicts,
        payments=payment_dicts,
        tickets=ticket_dicts,
        preferences=prefs_dict,
    )


# --- Send Reply ---

@router.post("/reply")
async def send_reply(
    data: SendReplyRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.whatsapp_id == data.whatsapp_number)
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    conversation = result.scalar_one_or_none()

    channel = getattr(conversation, "channel", CHANNEL_WHATSAPP) if conversation else CHANNEL_WHATSAPP

    try:
        if data.msg_type == "template" and data.template_name:
            send_result = await wa_service.send_template(
                data.whatsapp_number,
                data.template_name,
                params=data.template_params,
            )
        else:
            send_result = await messaging.send_text(channel, data.whatsapp_number, data.message)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Message delivery failed: {exc}")

    msg_id = None
    if send_result:
        msg_id = send_result.get("messages", [{}])[0].get("id") if "messages" in send_result else send_result.get("result", {}).get("message_id")

    if conversation:
        await log_message(
            conversation=conversation,
            whatsapp_msg_id=str(msg_id) if msg_id else None,
            direction="outbound",
            msg_type=data.msg_type,
            content={"body": data.message, "agent_id": str(current_user.id)},
            sender=f"agent:{current_user.id}",
            recipient=data.whatsapp_number,
            db=db,
        )

    return {"status": "sent", "message_id": msg_id}


# --- Bot Pause / Resume ---

@router.post("/conversations/{conversation_id}/pause")
async def pause_bot(
    conversation_id: uuid.UUID,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conversation = await escalation_service.pause_conversation(
        conversation_id, current_user.id, db
    )
    return {"status": "paused", "conversation_id": str(conversation.id)}


@router.post("/conversations/{conversation_id}/resume")
async def resume_bot(
    conversation_id: uuid.UUID,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conversation = await escalation_service.resume_bot(conversation_id, db)
    return {"status": "active", "conversation_id": str(conversation.id)}


# --- Assign / Reassign ---

@router.post("/conversations/{conversation_id}/assign")
async def assign_conversation(
    conversation_id: uuid.UUID,
    data: TicketAssignRequest,
    current_user: AdminUser = Depends(
        require_role("super_admin", "admin", "support_agent")
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.assigned_agent_id = data.agent_id
    await db.flush()
    return {
        "status": "assigned",
        "conversation_id": str(conversation_id),
        "agent_id": str(data.agent_id),
    }


# --- Close Conversation ---

@router.post("/conversations/{conversation_id}/close")
async def close_conversation(
    conversation_id: uuid.UUID,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conversation = await escalation_service.resume_bot(conversation_id, db)
    return {"status": "closed", "conversation_id": str(conversation.id)}


# --- Support Tickets ---

@router.get("/tickets", response_model=list[SupportTicketListOut])
async def list_tickets(
    status: str | None = None,
    department: str | None = None,
    priority: str | None = None,
    assigned_to_me: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SupportTicketListOut]:
    assigned_to = current_user.id if assigned_to_me else None
    tickets = await support_service.get_tickets(
        db,
        status=status,
        department=department,
        priority=priority,
        assigned_to=assigned_to,
        limit=limit,
        offset=offset,
    )
    return [SupportTicketListOut.model_validate(t) for t in tickets]


@router.get("/tickets/{ticket_id}", response_model=SupportTicketOut)
async def get_ticket(
    ticket_id: uuid.UUID,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportTicketOut:
    ticket = await support_service.get_ticket(ticket_id, db)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return SupportTicketOut.model_validate(ticket)


@router.post("/tickets/{ticket_id}/assign", response_model=SupportTicketOut)
async def assign_ticket(
    ticket_id: uuid.UUID,
    data: TicketAssignRequest,
    current_user: AdminUser = Depends(
        require_role("super_admin", "admin", "support_agent")
    ),
    db: AsyncSession = Depends(get_db),
) -> SupportTicketOut:
    ticket = await support_service.assign_ticket(ticket_id, data.agent_id, db)

    agent_result = await db.execute(
        select(AdminUser).where(AdminUser.id == data.agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    await notify_ticket_assigned(
        ticket_number=ticket.ticket_number,
        agent_name=agent.full_name if agent else str(data.agent_id),
        subject=ticket.subject,
    )

    return SupportTicketOut.model_validate(ticket)


@router.post("/tickets/{ticket_id}/close", response_model=SupportTicketOut)
async def close_ticket(
    ticket_id: uuid.UUID,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupportTicketOut:
    ticket = await support_service.close_ticket(ticket_id, db)
    return SupportTicketOut.model_validate(ticket)


# --- Internal Notes ---

@router.get(
    "/tickets/{ticket_id}/notes",
    response_model=list[InternalNoteOut],
)
async def list_notes(
    ticket_id: uuid.UUID,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InternalNoteOut]:
    notes = await support_service.get_notes_for_ticket(ticket_id, db)
    return [InternalNoteOut.model_validate(n) for n in notes]


@router.post(
    "/tickets/{ticket_id}/notes",
    response_model=InternalNoteOut,
    status_code=201,
)
async def create_note(
    ticket_id: uuid.UUID,
    data: InternalNoteCreate,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InternalNoteOut:
    ticket = await support_service.get_ticket(ticket_id, db)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    note = await support_service.add_note(
        ticket_id=ticket_id,
        author_id=current_user.id,
        content=data.content,
        db=db,
        conversation_id=data.conversation_id,
    )
    return InternalNoteOut.model_validate(note)


# --- Conversation Messages ---

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    limit: int = 100,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .limit(limit)
    )
    messages = list(result.scalars().all())
    return [
        {
            "id": str(m.id),
            "direction": m.direction,
            "msg_type": m.msg_type,
            "content": m.content,
            "sender": m.sender,
            "recipient": m.recipient,
            "delivery_status": m.delivery_status,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


# --- List Agents ---

@router.get("/agents", response_model=list[AdminUserOut])
async def list_agents(
    current_user: AdminUser = Depends(
        require_role("super_admin", "admin")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserOut]:
    result = await db.execute(
        select(AdminUser)
        .where(AdminUser.is_active == True)
        .order_by(AdminUser.full_name)
    )
    agents = list(result.scalars().all())
    return [AdminUserOut.model_validate(a) for a in agents]


# --- Ticket Stats ---

@router.get("/tickets/stats/counts")
async def ticket_stats(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    counts = await support_service.get_ticket_counts_by_status(db)
    return {"counts": counts}
