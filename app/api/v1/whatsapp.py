import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.correlation import get_correlation_id
from app.schemas.whatsapp import WhatsAppWebhookPayload
from app.services.conversation_engine import process_inbound_message
from app.services.whatsapp_service import wa_service
from app.utils.signature_verify import verify_whatsapp_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/webhook")
async def verify_webhook(request: Request) -> PlainTextResponse:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WA_VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return PlainTextResponse(challenge)

    logger.warning("Webhook verification failed.")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not settings.WA_APP_SECRET:
        logger.error("WA_APP_SECRET is not configured — rejecting webhook.")
        raise HTTPException(status_code=500, detail="Server misconfigured")

    if not verify_whatsapp_signature(body, signature, settings.WA_APP_SECRET):
        logger.warning("Invalid webhook signature.")
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = WhatsAppWebhookPayload.model_validate_json(body)

    for status in payload.extract_statuses():
        logger.info("Message %s status: %s", status.id, status.status)

    cid = get_correlation_id()

    for msg, contact in payload.extract_messages():
        if not msg.sender_number or not msg.type:
            continue

        contact_name = contact.profile.name if contact else None

        try:
            logger.info(
                "[%s] Processing %s message from %s",
                cid, msg.type, msg.sender_number,
            )
            await process_inbound_message(
                whatsapp_id=msg.sender_number,
                whatsapp_msg_id=msg.id,
                msg_type=msg.type,
                content=msg.model_dump(),
                user_input=msg.user_input,
                contact_name=contact_name,
                db=db,
            )
        except Exception:
            logger.exception(
                "[%s] Error processing message from %s", cid, msg.sender_number
            )

        if msg.id:
            try:
                await wa_service.mark_as_read(msg.id)
            except Exception:
                logger.debug("Failed to mark message %s as read", msg.id)

    return {"status": "ok"}
