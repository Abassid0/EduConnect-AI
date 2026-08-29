import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.admin_user import AdminUser
from app.services.conversation_engine import process_inbound_message
from app.services.messaging import CHANNEL_TELEGRAM
from app.services.telegram_service import telegram_service
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    if settings.TELEGRAM_WEBHOOK_SECRET:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if token != settings.TELEGRAM_WEBHOOK_SECRET:
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
            return JSONResponse({"status": "ignored"})
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
    except Exception:
        logger.exception("Error processing Telegram message from %s", chat_id)

    return JSONResponse({"status": "ok"})


@router.post("/setup")
async def setup_telegram_webhook(request: Request) -> dict:
    body = await request.json()
    webhook_url = body.get("url")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="url is required")

    result = await telegram_service.set_webhook(webhook_url)
    return result


@router.delete("/setup")
async def remove_telegram_webhook() -> dict:
    result = await telegram_service.delete_webhook()
    return result


@router.get("/me")
async def get_bot_info() -> dict:
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
