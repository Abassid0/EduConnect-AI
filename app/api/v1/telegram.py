import hmac
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.rate_limit import limiter
from app.models.admin_user import AdminUser
from app.models.conversation import Conversation
from app.services.conversation_engine import log_message, process_inbound_message
from app.services.messaging import CHANNEL_TELEGRAM
from app.services.telegram_service import telegram_service
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


async def _handle_group_reply(
    message: dict, chat: dict, db: AsyncSession,
) -> JSONResponse:
    """Handle replies in the admin notification group.

    When an admin replies to a bot notification, extract the user ID from
    the original notification and forward the reply to that user.
    """
    admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    if not admin_chat_id or str(chat.get("id")) != admin_chat_id:
        return JSONResponse({"status": "ignored"})

    reply_to = message.get("reply_to_message")
    reply_text = message.get("text", "").strip()
    if not reply_to or not reply_text:
        return JSONResponse({"status": "ignored"})

    original_from = reply_to.get("from", {})
    if not original_from.get("is_bot"):
        return JSONResponse({"status": "ignored"})

    original_text = reply_to.get("text", "")
    user_match = re.search(r"User:\s*(\d+)", original_text)
    if not user_match:
        return JSONResponse({"status": "ignored"})

    user_chat_id = user_match.group(1)
    admin_name = message.get("from", {}).get("first_name", "Admin")

    try:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.whatsapp_id == user_chat_id)
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        conversation = result.scalar_one_or_none()

        await telegram_service.send_text(
            user_chat_id,
            f"*{admin_name}:* {reply_text}",
        )

        if conversation:
            await log_message(
                conversation=conversation,
                whatsapp_msg_id=f"tg_group_{message.get('message_id', '')}",
                direction="outbound",
                msg_type="text",
                content={"body": reply_text, "agent_name": admin_name},
                sender=f"agent:telegram:{admin_name}",
                recipient=user_chat_id,
                db=db,
            )

        await telegram_service.send_text(
            admin_chat_id,
            f"Reply sent to user {user_chat_id}",
        )
    except Exception:
        logger.exception("Failed to forward group reply to user %s", user_chat_id)
        try:
            await telegram_service.send_text(
                admin_chat_id,
                f"Failed to send reply to user {user_chat_id}. Please try from the dashboard.",
            )
        except Exception:
            pass

    return JSONResponse({"status": "ok"})


@router.post("/webhook")
@limiter.limit("30/minute")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        logger.error("TELEGRAM_WEBHOOK_SECRET not configured — rejecting webhook")
        raise HTTPException(status_code=500, detail="Server misconfigured")

    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(token, settings.TELEGRAM_WEBHOOK_SECRET):
        raise HTTPException(status_code=403, detail="Invalid secret token")

    payload = await request.json()

    callback_query = payload.get("callback_query")
    message = payload.get("message")

    if callback_query:
        chat = callback_query.get("message", {}).get("chat", {})
        if chat.get("type") in ("group", "supergroup", "channel"):
            return JSONResponse({"status": "ignored"})
        chat_id = str(chat.get("id", ""))
        user_input = callback_query.get("data", "")
        from_user = callback_query.get("from", {})
        contact_name = from_user.get("first_name", "")
        callback_id = callback_query.get("id")
        msg_id = f"tg_cb_{callback_query.get('id', '')}"

        try:
            await telegram_service.answer_callback_query(callback_id)
        except Exception:
            logger.debug("Failed to answer callback query %s", callback_id)

    elif message:
        chat = message.get("chat", {})
        if chat.get("type") in ("group", "supergroup", "channel"):
            return await _handle_group_reply(message, chat, db)
        chat_id = str(chat.get("id", ""))
        user_input = message.get("text", "")
        from_user = message.get("from", {})
        contact_name = from_user.get("first_name", "")
        msg_id = f"tg_{message.get('message_id', '')}"
    else:
        return JSONResponse({"status": "ignored"})

    if not chat_id or not user_input:
        return JSONResponse({"status": "ignored"})

    try:
        await process_inbound_message(
            whatsapp_id=chat_id,
            whatsapp_msg_id=msg_id,
            msg_type="text",
            content={"text": {"body": user_input}},
            user_input=user_input,
            contact_name=contact_name,
            db=db,
            channel=CHANNEL_TELEGRAM,
        )
        await db.commit()
    except Exception:
        logger.exception("Error processing Telegram message from %s", chat_id)
        await db.rollback()

    return JSONResponse({"status": "ok"})


@router.post("/setup")
async def setup_telegram_webhook(
    request: Request,
    _user: AdminUser = Depends(get_current_user),
) -> dict:
    body = await request.json()
    webhook_url = body.get("url")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="url is required")

    result = await telegram_service.set_webhook(webhook_url)
    return result


@router.delete("/setup")
async def remove_telegram_webhook(
    _user: AdminUser = Depends(get_current_user),
) -> dict:
    result = await telegram_service.delete_webhook()
    return result


@router.get("/me")
async def get_bot_info(
    _user: AdminUser = Depends(get_current_user),
) -> dict:
    result = await telegram_service.get_me()
    return result


# ---------------------------------------------------------------------------
# Template testing — send any template to Telegram to preview before
# submitting to Meta WhatsApp Business API
# ---------------------------------------------------------------------------

class TemplateTestRequest(BaseModel):
    chat_id: str
    template_name: str
    params: list[str] = []


@router.post("/test-template")
async def test_template(
    data: TemplateTestRequest,
    _user: AdminUser = Depends(get_current_user),
) -> dict:
    from app.services.template_registry import get_template_body, render

    body = get_template_body(data.template_name)
    if body is None:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{data.template_name}' not found in registry",
        )

    rendered = render(data.template_name, data.params or None)

    try:
        await telegram_service.send_text(data.chat_id, rendered)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Telegram delivery failed: {exc}",
        )

    return {
        "status": "sent",
        "template": data.template_name,
        "chat_id": data.chat_id,
        "rendered_preview": rendered,
    }


@router.get("/templates")
async def list_templates(
    _user: AdminUser = Depends(get_current_user),
) -> list[dict]:
    from app.services.template_registry import list_templates as _list
    return _list()
