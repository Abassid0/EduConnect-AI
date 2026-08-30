import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.flows import FlowResult
from app.flows.main_menu import FLOW_MAP, build_main_menu, handle_menu_selection
from app.models.ai_interaction import AIInteraction
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.parent import Parent
from app.services import analytics_service, messaging
from app.services.messaging import CHANNEL_WHATSAPP

logger = logging.getLogger(__name__)


async def get_or_create_conversation(
    whatsapp_id: str, db: AsyncSession, channel: str = CHANNEL_WHATSAPP,
) -> Conversation:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.whatsapp_id == whatsapp_id)
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    conversation = result.scalar_one_or_none()

    if conversation is None:
        conversation = Conversation(
            id=uuid.uuid4(),
            whatsapp_id=whatsapp_id,
            channel=channel,
            status="active",
            flow_data={},
        )
        db.add(conversation)
        await db.flush()

        await analytics_service.track_event(
            "conversation_start",
            db,
            whatsapp_number=whatsapp_id,
            conversation_id=conversation.id,
        )
    elif conversation.channel != channel:
        conversation.channel = channel
        await db.flush()

    return conversation


async def log_message(
    conversation: Conversation,
    whatsapp_msg_id: str | None,
    direction: str,
    msg_type: str,
    content: dict[str, Any],
    sender: str,
    recipient: str,
    db: AsyncSession,
) -> Message:
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        whatsapp_msg_id=whatsapp_msg_id,
        direction=direction,
        msg_type=msg_type,
        content=content,
        sender=sender,
        recipient=recipient,
    )
    db.add(message)
    conversation.last_message_at = datetime.now(timezone.utc)
    await db.flush()
    return message


async def _send_replies(
    to: str,
    replies: list[dict[str, Any]],
    conversation: Conversation,
    db: AsyncSession,
    channel: str = CHANNEL_WHATSAPP,
) -> None:
    for reply_payload in replies:
        try:
            result = await messaging.send_payload(channel, to, reply_payload)
            wa_msg_id = (
                result.get("messages", [{}])[0].get("id") if result else None
            )
            await log_message(
                conversation=conversation,
                whatsapp_msg_id=wa_msg_id,
                direction="outbound",
                msg_type=reply_payload.get("type", "text"),
                content=reply_payload,
                sender="system",
                recipient=to,
                db=db,
            )
        except Exception:
            logger.exception("Failed to send reply to %s", to)


async def _get_flow_handler(flow_name: str):
    if flow_name == "main_menu":
        return None
    if flow_name == "registration":
        from app.flows.registration_flow import handle_step
        return handle_step
    if flow_name == "enquiry":
        from app.flows.enquiry_flow import handle_step
        return handle_step
    if flow_name == "my_account":
        from app.flows.my_account_flow import handle_step
        return handle_step
    if flow_name == "payment":
        from app.flows.payment_flow import handle_step
        return handle_step
    if flow_name == "notification_prefs":
        from app.flows.notification_prefs_flow import handle_step
        return handle_step
    if flow_name == "support":
        from app.flows.support_flow import handle_step
        return handle_step
    if flow_name == "partnership":
        from app.flows.partnership_flow import handle_step
        return handle_step
    if flow_name == "billing":
        from app.flows.billing_flow import handle_step
        return handle_step
    if flow_name == "calendar":
        from app.flows.calendar_flow import handle_step
        return handle_step
    if flow_name == "permission":
        from app.flows.permission_flow import handle_step
        return handle_step
    if flow_name == "payment_plan":
        from app.flows.payment_plan_flow import handle_step
        return handle_step
    if flow_name == "report_card":
        from app.flows.report_card_flow import handle_step
        return handle_step
    return None


async def _handle_flow_result(
    result: FlowResult,
    whatsapp_id: str,
    conversation: Conversation,
    db: AsyncSession,
    channel: str = CHANNEL_WHATSAPP,
) -> None:
    if result.all_replies:
        await _send_replies(whatsapp_id, result.all_replies, conversation, db, channel)

    if result.flow_complete:
        conversation.current_flow = None
        conversation.current_step = None
        conversation.flow_data = {}
        flag_modified(conversation, "flow_data")
        return

    if result.next_flow:
        conversation.current_flow = result.next_flow
        conversation.current_step = result.next_step
        conversation.flow_data = dict(result.flow_data)
        flag_modified(conversation, "flow_data")

        if result.next_flow == "main_menu":
            menu_payload = build_main_menu(whatsapp_id)
            await _send_replies(whatsapp_id, [menu_payload], conversation, db, channel)
            return

        handler = await _get_flow_handler(result.next_flow)
        if handler and result.next_step == "start":
            entry_result = await handler(
                step="start",
                user_input="",
                flow_data=result.flow_data,
                conversation=conversation,
                db=db,
            )
            await _handle_flow_result(entry_result, whatsapp_id, conversation, db, channel)
        elif handler is None and result.next_flow in FLOW_MAP.values():
            await messaging.send_text(
                channel,
                whatsapp_id,
                "This feature is coming soon! Returning to the main menu.",
            )
            conversation.current_flow = None
            conversation.current_step = None
            conversation.flow_data = {}
            flag_modified(conversation, "flow_data")
            menu_payload = build_main_menu(whatsapp_id)
            await _send_replies(whatsapp_id, [menu_payload], conversation, db, channel)
    else:
        conversation.current_step = result.next_step
        conversation.flow_data = dict(result.flow_data)
        flag_modified(conversation, "flow_data")


async def process_inbound_message(
    whatsapp_id: str,
    whatsapp_msg_id: str | None,
    msg_type: str,
    content: dict[str, Any],
    user_input: str,
    contact_name: str | None,
    db: AsyncSession,
    channel: str = CHANNEL_WHATSAPP,
) -> None:
    conversation = await get_or_create_conversation(whatsapp_id, db, channel)

    await log_message(
        conversation=conversation,
        whatsapp_msg_id=whatsapp_msg_id,
        direction="inbound",
        msg_type=msg_type,
        content=content,
        sender=whatsapp_id,
        recipient="system",
        db=db,
    )

    if user_input.lower().strip() == "menu":
        conversation.current_flow = "main_menu"
        conversation.current_step = "show"
        conversation.flow_data = {}
        menu_payload = build_main_menu(whatsapp_id)
        await _send_replies(whatsapp_id, [menu_payload], conversation, db, channel)
        return

    if not conversation.current_flow:
        from app.flows.calendar_flow import CALENDAR_KEYWORDS
        if user_input.lower().strip() in CALENDAR_KEYWORDS:
            conversation.current_flow = "calendar"
            conversation.current_step = "start"
            conversation.flow_data = {}
            handler = await _get_flow_handler("calendar")
            if handler:
                result = await handler(
                    step="start",
                    user_input="",
                    flow_data={},
                    conversation=conversation,
                    db=db,
                )
                await _handle_flow_result(result, whatsapp_id, conversation, db, channel)
                return

    if conversation.status == "paused_for_agent":
        logger.info(
            "Conversation %s is paused for agent — message logged, bot silent.",
            conversation.id,
        )
        return

    # Shared parent lookup for interrupt blocks below
    _parent = None
    if not conversation.current_flow:
        try:
            from sqlalchemy import select as sa_select
            from app.models.parent import Parent as _Parent
            _parent_result = await db.execute(
                sa_select(_Parent).where(_Parent.whatsapp_number == whatsapp_id)
            )
            _parent = _parent_result.scalar_one_or_none()
        except Exception:
            logger.exception("Parent lookup for interrupts failed for %s", whatsapp_id)

    # Interrupt 1 — pending permission slip (highest priority)
    if not conversation.current_flow:
        try:
            from app.services import permission_service as _ps
            if _parent:
                _pending = await _ps.get_pending_slips_for_parent(_parent.id, db)
                if _pending:
                    _slip = _pending[0]
                    conversation.current_flow = "permission"
                    conversation.current_step = "start"
                    conversation.flow_data = {"slip_id": str(_slip.id)}
                    from app.flows.permission_flow import handle_step as _perm_handle
                    _perm_result = await _perm_handle(
                        step="start",
                        user_input="",
                        flow_data={"slip_id": str(_slip.id)},
                        conversation=conversation,
                        db=db,
                    )
                    await _handle_flow_result(_perm_result, whatsapp_id, conversation, db, channel)
                    return
        except Exception:
            logger.exception("Permission slip interrupt failed for %s", whatsapp_id)

    # Interrupt 2 — unacknowledged report card (fires after slip is cleared)
    if not conversation.current_flow:
        try:
            from app.services import report_card_service as _rcs
            if _parent:
                _pending_rc = await _rcs.get_unacknowledged_for_parent(_parent.id, db)
                if _pending_rc:
                    _rc = _pending_rc[0]
                    conversation.current_flow = "report_card"
                    conversation.current_step = "start"
                    conversation.flow_data = {"report_card_id": str(_rc.id)}
                    from app.flows.report_card_flow import handle_step as _rc_handle
                    _rc_result = await _rc_handle(
                        step="start",
                        user_input="",
                        flow_data={"report_card_id": str(_rc.id)},
                        conversation=conversation,
                        db=db,
                    )
                    await _handle_flow_result(_rc_result, whatsapp_id, conversation, db, channel)
                    return
        except Exception:
            logger.exception("Report card interrupt failed for %s", whatsapp_id)

    if conversation.current_flow and conversation.current_step:
        if conversation.current_flow == "main_menu":
            result = await handle_menu_selection(
                user_input, conversation.flow_data or {}
            )
        else:
            flow_handler = await _get_flow_handler(conversation.current_flow)
            if not flow_handler:
                await messaging.send_text(
                    channel,
                    whatsapp_id,
                    "This feature is coming soon! Returning to the main menu.",
                )
                conversation.current_flow = None
                conversation.current_step = None
                conversation.flow_data = {}
                menu_payload = build_main_menu(whatsapp_id)
                await _send_replies(
                    whatsapp_id, [menu_payload], conversation, db, channel
                )
                return

            result = await flow_handler(
                step=conversation.current_step,
                user_input=user_input,
                flow_data=conversation.flow_data or {},
                conversation=conversation,
                db=db,
            )

        await _handle_flow_result(result, whatsapp_id, conversation, db, channel)
        return

    if _is_natural_language_query(user_input):
        await _handle_ai_fallback(
            user_input, whatsapp_id, conversation, db, channel
        )
        return

    greeting = "Hi"
    if contact_name:
        greeting = f"Hi {contact_name}"

    await messaging.send_text(
        channel,
        whatsapp_id,
        f"{greeting}! Welcome to EduConnect AI. Let me show you what I can help with.",
    )

    conversation.current_flow = "main_menu"
    conversation.current_step = "show"
    menu_payload = build_main_menu(whatsapp_id)
    await _send_replies(whatsapp_id, [menu_payload], conversation, db, channel)


def _is_natural_language_query(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 5:
        return False
    if stripped.startswith("menu_"):
        return False
    indicators = [
        "?", "how much", "how do", "when is", "what is", "where is",
        "i want", "i need", "can i", "can you", "please", "help me",
        "tell me", "do you", "is there", "are there", "i'd like",
        "register", "payment", "schedule", "class", "programme",
        "program", "price", "cost", "fee", "my child", "my son",
        "my daughter", "my kid", "speak to", "talk to", "someone",
        "human", "agent", "support", "refund", "receipt",
        "how old", "age", "slot", "available",
    ]
    lower = stripped.lower()
    if any(ind in lower for ind in indicators):
        return True
    if len(stripped.split()) >= 3:
        return True
    return False


async def _handle_ai_fallback(
    user_input: str,
    whatsapp_id: str,
    conversation: Conversation,
    db: AsyncSession,
    channel: str = CHANNEL_WHATSAPP,
) -> None:
    from app.services import ai_service

    parent_result = await db.execute(
        select(Parent).where(Parent.whatsapp_number == whatsapp_id)
    )
    parent = parent_result.scalar_one_or_none()
    parent_id = parent.id if parent else None

    ai_result = await ai_service.handle_ai_query(
        user_query=user_input,
        whatsapp_number=whatsapp_id,
        conversation_id=conversation.id,
        db=db,
    )

    interaction = AIInteraction(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        parent_id=parent_id,
        user_query=user_input,
        tools_called=ai_result["tools_called"],
        ai_response=ai_result["response"],
        confidence_score=ai_result["confidence"],
        escalated=ai_result["escalate"],
        response_time_ms=ai_result["response_time_ms"],
    )
    db.add(interaction)
    await db.flush()

    await analytics_service.track_event(
        "ai_query",
        db,
        whatsapp_number=whatsapp_id,
        conversation_id=conversation.id,
        properties={
            "confidence": ai_result["confidence"],
            "tools_used": [tc["name"] for tc in ai_result["tools_called"]],
            "escalated": ai_result["escalate"],
            "response_time_ms": ai_result["response_time_ms"],
        },
    )

    if ai_result["escalate"]:
        from app.services import escalation_service

        ai_response = ai_result["response"]
        try:
            await messaging.send_text(channel, whatsapp_id, ai_response)
            await log_message(
                conversation=conversation,
                whatsapp_msg_id=None,
                direction="outbound",
                msg_type="text",
                content={"text": {"body": ai_response}},
                sender="ai_assistant",
                recipient=whatsapp_id,
                db=db,
            )
        except Exception:
            logger.exception("Failed to send AI response before escalation")

        await escalation_service.escalate(
            conversation_id=conversation.id,
            whatsapp_number=whatsapp_id,
            reason="low_confidence",
            db=db,
            description=f"AI confidence: {ai_result['confidence']}. Query: {user_input}",
            parent_id=parent_id,
        )
        return

    response_text = ai_result["response"]
    try:
        await messaging.send_text(channel, whatsapp_id, response_text)
        await log_message(
            conversation=conversation,
            whatsapp_msg_id=None,
            direction="outbound",
            msg_type="text",
            content={"text": {"body": response_text}},
            sender="ai_assistant",
            recipient=whatsapp_id,
            db=db,
        )
    except Exception:
        logger.exception("Failed to send AI response to %s", whatsapp_id)
