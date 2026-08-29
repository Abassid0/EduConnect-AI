import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_whatsapp_message(self, payload: dict) -> dict:
    """
    Async-to-sync bridge for Celery workers.

    In Phase 1 we process messages synchronously in the webhook handler
    for simplicity. This task exists for background processing when
    the webhook needs to return immediately under load — route the
    payload here via `process_whatsapp_message.delay(payload)`.
    """
    from app.database import async_session_factory
    from app.schemas.whatsapp import WhatsAppWebhookPayload
    from app.services.conversation_engine import process_inbound_message
    from app.services.whatsapp_service import wa_service

    async def _process():
        parsed = WhatsAppWebhookPayload.model_validate(payload)
        async with async_session_factory() as db:
            try:
                for msg, contact in parsed.extract_messages():
                    if not msg.sender_number or not msg.type:
                        continue
                    contact_name = contact.profile.name if contact else None
                    await process_inbound_message(
                        whatsapp_id=msg.sender_number,
                        whatsapp_msg_id=msg.id,
                        msg_type=msg.type,
                        content=msg.model_dump(),
                        user_input=msg.user_input,
                        contact_name=contact_name,
                        db=db,
                    )
                    if msg.id:
                        try:
                            await wa_service.mark_as_read(msg.id)
                        except Exception:
                            logger.debug("Failed to mark %s as read", msg.id)
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    try:
        _run_async(_process())
        return {"status": "processed"}
    except Exception as exc:
        logger.exception("Failed to process webhook payload")
        raise self.retry(exc=exc)
