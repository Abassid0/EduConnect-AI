import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

import anthropic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.class_schedule import ClassSchedule
from app.models.enrollment import Enrollment
from app.models.parent import Parent
from app.models.payment import Payment
from app.models.programme import Programme
from app.models.student import Student
from app.services import support_service

logger = logging.getLogger(__name__)

WAT = timezone(timedelta(hours=1))

SYSTEM_PROMPT = (
    "You are Edpassare's helpful assistant for parents. "
    "Edpassare's tagline is 'Learning Without Fear. Growing Without Limits.'\n\n"
    "You help with programme enquiries, registration, payments, and class schedules. "
    "You ONLY use the provided functions to access data. "
    "You NEVER make up programme names, prices, or schedules. "
    "If you cannot answer confidently, say so and offer to connect the parent to a staff member.\n\n"
    "Guidelines:\n"
    "- Keep responses concise for WhatsApp (max 3-4 short paragraphs)\n"
    "- Be warm and conversational\n"
    "- Use naira sign (NGN) for prices\n"
    "- Format schedules clearly with days and times\n"
    "- Never expose internal IDs, database errors, or system details\n"
    "- If asked about something outside education services, politely redirect\n"
    "- When suggesting registration, tell them to type 'menu' and select 'Register a Student'\n"
    "- When suggesting payment, tell them to type 'menu' and select 'Make Payment'\n"
)

TOOLS = [
    {
        "name": "get_programmes",
        "description": (
            "Search for available education programmes. "
            "Can filter by child's age and/or programme level."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "age": {
                    "type": "integer",
                    "description": "Child's age to filter age-appropriate programmes",
                },
                "level": {
                    "type": "string",
                    "description": "Programme level to filter by (e.g. beginner, intermediate)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_programme_details",
        "description": "Get full details of a specific programme including schedules and available slots.",
        "input_schema": {
            "type": "object",
            "properties": {
                "programme_id": {
                    "type": "string",
                    "description": "The programme ID to look up",
                },
            },
            "required": ["programme_id"],
        },
    },
    {
        "name": "get_payment_status",
        "description": "Check payment status for a parent's children. Returns pending and completed payments.",
        "input_schema": {
            "type": "object",
            "properties": {
                "parent_phone": {
                    "type": "string",
                    "description": "The parent's WhatsApp phone number",
                },
            },
            "required": ["parent_phone"],
        },
    },
    {
        "name": "get_student_info",
        "description": "Look up a parent's registered children and their enrolment status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "parent_phone": {
                    "type": "string",
                    "description": "The parent's WhatsApp phone number",
                },
            },
            "required": ["parent_phone"],
        },
    },
    {
        "name": "create_registration_intent",
        "description": (
            "Start a registration for a child in a programme. "
            "Returns a confirmation prompt for the parent to review."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "parent_phone": {
                    "type": "string",
                    "description": "The parent's WhatsApp phone number",
                },
                "child_name": {
                    "type": "string",
                    "description": "The child's full name",
                },
                "programme_id": {
                    "type": "string",
                    "description": "The programme to register for",
                },
            },
            "required": ["parent_phone", "child_name", "programme_id"],
        },
    },
    {
        "name": "get_class_schedule",
        "description": "Get upcoming class schedule for a specific student.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "The student's ID",
                },
            },
            "required": ["student_id"],
        },
    },
    {
        "name": "get_support_departments",
        "description": "Get the list of support departments available for routing queries.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# --- Controlled backend functions ---

async def _tool_get_programmes(
    db: AsyncSession, age: int | None = None, level: str | None = None
) -> list[dict]:
    stmt = select(Programme).where(Programme.is_active.is_(True))
    if age is not None:
        stmt = stmt.where(
            (Programme.age_range_min.is_(None) | (Programme.age_range_min <= age)),
            (Programme.age_range_max.is_(None) | (Programme.age_range_max >= age)),
        )
    if level:
        stmt = stmt.where(Programme.level.ilike(f"%{level}%"))
    stmt = stmt.order_by(Programme.name)
    result = await db.execute(stmt)
    programmes = result.scalars().all()

    items = []
    for p in programmes:
        schedules = []
        for s in (p.schedules or []):
            schedules.append(s.display)
        items.append({
            "id": str(p.id),
            "name": p.name,
            "description": p.description or "",
            "age_range": f"{p.age_range_min or '?'}-{p.age_range_max or '?'} years",
            "level": p.level or "All levels",
            "fee": f"NGN {p.fee:,.2f}",
            "duration": p.duration or "N/A",
            "delivery_mode": p.delivery_mode or "N/A",
            "available_slots": p.available_slots,
            "schedules": schedules,
        })
    return items


async def _tool_get_programme_details(
    db: AsyncSession, programme_id: str
) -> dict:
    try:
        pid = uuid.UUID(programme_id)
    except ValueError:
        return {"error": "Invalid programme ID"}

    result = await db.execute(select(Programme).where(Programme.id == pid))
    p = result.scalar_one_or_none()
    if not p:
        return {"error": "Programme not found"}

    sched_result = await db.execute(
        select(ClassSchedule)
        .where(ClassSchedule.programme_id == pid)
        .order_by(ClassSchedule.day_of_week)
    )
    schedules = [s.display for s in sched_result.scalars().all()]

    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description or "",
        "age_range": f"{p.age_range_min or '?'}-{p.age_range_max or '?'} years",
        "level": p.level or "All levels",
        "fee": f"NGN {p.fee:,.2f}",
        "duration": p.duration or "N/A",
        "delivery_mode": p.delivery_mode or "N/A",
        "available_slots": p.available_slots,
        "instructor": p.instructor or "TBA",
        "schedules": schedules,
    }


async def _tool_get_payment_status(
    db: AsyncSession, parent_phone: str
) -> list[dict]:
    result = await db.execute(
        select(Parent).where(Parent.whatsapp_number == parent_phone)
    )
    parent = result.scalar_one_or_none()
    if not parent:
        return []

    student_result = await db.execute(
        select(Student).where(Student.parent_id == parent.id)
    )
    students = student_result.scalars().all()
    if not students:
        return []

    student_ids = [s.id for s in students]
    student_map = {s.id: s.full_name for s in students}

    pay_result = await db.execute(
        select(Payment)
        .where(Payment.student_id.in_(student_ids))
        .order_by(Payment.created_at.desc())
        .limit(20)
    )
    payments = pay_result.scalars().all()

    items = []
    for pay in payments:
        prog_result = await db.execute(
            select(Programme.name).where(Programme.id == pay.programme_id)
        )
        prog_name = prog_result.scalar_one_or_none() or "Unknown"

        items.append({
            "student_name": student_map.get(pay.student_id, "Unknown"),
            "programme": prog_name,
            "amount": f"NGN {pay.amount:,.2f}",
            "status": pay.status,
            "reference": pay.reference,
            "date": pay.created_at.strftime("%d %b %Y") if pay.created_at else "N/A",
        })
    return items


async def _tool_get_student_info(
    db: AsyncSession, parent_phone: str
) -> list[dict]:
    result = await db.execute(
        select(Parent).where(Parent.whatsapp_number == parent_phone)
    )
    parent = result.scalar_one_or_none()
    if not parent:
        return []

    student_result = await db.execute(
        select(Student)
        .where(Student.parent_id == parent.id)
        .order_by(Student.created_at)
    )
    students = student_result.scalars().all()

    items = []
    for s in students:
        enr_result = await db.execute(
            select(Enrollment).where(Enrollment.student_id == s.id)
        )
        enrollments = enr_result.scalars().all()

        enr_list = []
        for e in enrollments:
            prog_result = await db.execute(
                select(Programme.name).where(Programme.id == e.programme_id)
            )
            prog_name = prog_result.scalar_one_or_none() or "Unknown"
            enr_list.append({
                "programme": prog_name,
                "status": e.status,
            })

        items.append({
            "name": s.full_name,
            "registration_id": s.registration_id,
            "age": s.age,
            "enrollments": enr_list,
        })
    return items


async def _tool_create_registration_intent(
    db: AsyncSession, parent_phone: str, child_name: str, programme_id: str
) -> dict:
    try:
        pid = uuid.UUID(programme_id)
    except ValueError:
        return {"error": "Invalid programme ID"}

    result = await db.execute(select(Programme).where(Programme.id == pid))
    programme = result.scalar_one_or_none()
    if not programme:
        return {"error": "Programme not found"}

    if programme.available_slots <= 0:
        return {
            "error": "No slots available",
            "programme": programme.name,
        }

    return {
        "status": "ready",
        "message": (
            f"To register {child_name} for {programme.name} "
            f"(NGN {programme.fee:,.2f}), please type 'menu' and "
            f"select 'Register a Student' to complete the full registration process."
        ),
        "programme": programme.name,
        "fee": f"NGN {programme.fee:,.2f}",
        "child_name": child_name,
    }


async def _tool_get_class_schedule(
    db: AsyncSession, student_id: str
) -> list[dict]:
    try:
        sid = uuid.UUID(student_id)
    except ValueError:
        return [{"error": "Invalid student ID"}]

    enr_result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == sid, Enrollment.status.in_(["active", "confirmed"]))
    )
    enrollments = enr_result.scalars().all()

    schedules = []
    for e in enrollments:
        prog_result = await db.execute(
            select(Programme).where(Programme.id == e.programme_id)
        )
        prog = prog_result.scalar_one_or_none()
        if not prog:
            continue

        sched_result = await db.execute(
            select(ClassSchedule)
            .where(ClassSchedule.programme_id == e.programme_id)
            .order_by(ClassSchedule.day_of_week)
        )
        for s in sched_result.scalars().all():
            schedules.append({
                "programme": prog.name,
                "day": s.day_name,
                "time": f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}",
            })
    return schedules


def _tool_get_support_departments() -> list[dict]:
    return [
        {"id": dept, "name": dept.replace("_", " ").title()}
        for dept in support_service.DEPARTMENTS
    ]


TOOL_DISPATCH = {
    "get_programmes": _tool_get_programmes,
    "get_programme_details": _tool_get_programme_details,
    "get_payment_status": _tool_get_payment_status,
    "get_student_info": _tool_get_student_info,
    "create_registration_intent": _tool_create_registration_intent,
    "get_class_schedule": _tool_get_class_schedule,
}


async def _execute_tool(
    tool_name: str, tool_input: dict, db: AsyncSession
) -> str:
    if tool_name == "get_support_departments":
        import json
        return json.dumps(_tool_get_support_departments())

    handler = TOOL_DISPATCH.get(tool_name)
    if not handler:
        return '{"error": "Unknown function"}'

    try:
        result = await handler(db, **tool_input)
        import json
        return json.dumps(result, default=str)
    except Exception:
        logger.exception("Tool execution failed: %s", tool_name)
        return '{"error": "Unable to retrieve information right now"}'


# --- Rate limiting (in-memory per conversation, 10 calls / 5 min) ---

_rate_limits: dict[str, list[float]] = {}
AI_RATE_LIMIT = 10
AI_RATE_WINDOW = 300


def _check_rate_limit(conversation_id: str) -> bool:
    now = time.time()
    calls = _rate_limits.get(conversation_id, [])
    calls = [t for t in calls if now - t < AI_RATE_WINDOW]
    _rate_limits[conversation_id] = calls
    if len(calls) >= AI_RATE_LIMIT:
        return False
    calls.append(now)
    return True


# --- Main AI handler ---

async def handle_ai_query(
    user_query: str,
    whatsapp_number: str,
    conversation_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """
    Returns:
        {
            "response": str,           # text to send to parent
            "confidence": float,        # 0.0 - 1.0
            "tools_called": list[dict], # [{name, input, output}]
            "escalate": bool,           # whether to escalate to human
            "response_time_ms": int,
        }
    """
    start_ms = time.monotonic()
    conv_id_str = str(conversation_id)

    if not _check_rate_limit(conv_id_str):
        return {
            "response": (
                "I've been getting quite a few questions! "
                "Let me connect you with a team member who can help more quickly."
            ),
            "confidence": 0.0,
            "tools_called": [],
            "escalate": True,
            "response_time_ms": int((time.monotonic() - start_ms) * 1000),
        }

    if not settings.ANTHROPIC_API_KEY:
        return {
            "response": (
                "I'm not able to process that right now. "
                "Please type 'menu' to see available options, "
                "or I can connect you with a staff member."
            ),
            "confidence": 0.0,
            "tools_called": [],
            "escalate": False,
            "response_time_ms": int((time.monotonic() - start_ms) * 1000),
        }

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    messages = [{"role": "user", "content": user_query}]
    tools_called = []

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        while response.stop_reason == "tool_use":
            tool_blocks = [b for b in response.content if b.type == "tool_use"]

            tool_results = []
            for block in tool_blocks:
                tool_output = await _execute_tool(block.name, block.input, db)
                tools_called.append({
                    "name": block.name,
                    "input": block.input,
                    "output": tool_output[:500],
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": tool_output,
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

        text_blocks = [b.text for b in response.content if b.type == "text"]
        ai_response = "\n".join(text_blocks).strip()

        confidence = _estimate_confidence(ai_response, tools_called, response)
        escalate = confidence < 0.4 or _contains_escalation_intent(ai_response)

        elapsed_ms = int((time.monotonic() - start_ms) * 1000)

        return {
            "response": ai_response,
            "confidence": confidence,
            "tools_called": tools_called,
            "escalate": escalate,
            "response_time_ms": elapsed_ms,
        }

    except anthropic.APIError:
        logger.exception("Anthropic API error")
        elapsed_ms = int((time.monotonic() - start_ms) * 1000)
        return {
            "response": (
                "I'm having a little trouble right now. "
                "Please type 'menu' to see available options, "
                "or I can connect you with a staff member."
            ),
            "confidence": 0.0,
            "tools_called": tools_called,
            "escalate": False,
            "response_time_ms": elapsed_ms,
        }


def _estimate_confidence(
    response_text: str, tools_called: list[dict], api_response
) -> float:
    score = 0.7

    if tools_called:
        score += 0.15
        has_error = any('"error"' in (tc.get("output", "")) for tc in tools_called)
        if has_error:
            score -= 0.3

    low_confidence_phrases = [
        "i'm not sure",
        "i don't have",
        "i cannot",
        "i can't confirm",
        "unable to",
        "don't know",
        "not certain",
        "no information",
    ]
    lower_response = response_text.lower()
    for phrase in low_confidence_phrases:
        if phrase in lower_response:
            score -= 0.25
            break

    if "connect you" in lower_response or "staff member" in lower_response:
        score -= 0.2

    if api_response.stop_reason == "end_turn" and len(response_text) > 20:
        score += 0.05

    return max(0.0, min(1.0, round(score, 2)))


def _contains_escalation_intent(response_text: str) -> bool:
    lower = response_text.lower()
    markers = [
        "connect you with a staff member",
        "connect you to a team member",
        "speak to someone",
        "transfer you",
        "let me get a human",
    ]
    return any(m in lower for m in markers)
