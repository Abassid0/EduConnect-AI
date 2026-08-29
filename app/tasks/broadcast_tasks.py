import asyncio
import logging
import time
import uuid

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def fan_out_broadcast(self, broadcast_id: str) -> dict:
    from app.database import async_session_factory

    async def _process():
        async with async_session_factory() as db:
            try:
                result = await _send_broadcast(broadcast_id, db)
                await db.commit()
                return result
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.exception("Broadcast fan-out failed for %s", broadcast_id)
        raise self.retry(exc=exc)


async def _send_broadcast(broadcast_id_str: str, db) -> dict:
    from app.services import broadcast_service
    from app.services.notification_service import send_notification

    bid = uuid.UUID(broadcast_id_str)
    broadcast = await broadcast_service.get_broadcast(bid, db)
    if not broadcast:
        logger.error("Broadcast %s not found", broadcast_id_str)
        return {"error": "not_found"}

    parents = await broadcast_service.resolve_recipients(
        broadcast.segment_type, broadcast.segment_value, db
    )

    delivered = 0
    for parent in parents:
        event_key = f"broadcast:{broadcast_id_str}:{parent.id}"
        try:
            await send_notification(
                recipient_whatsapp=parent.whatsapp_number,
                notification_type="broadcast",
                message_body=broadcast.body,
                db=db,
                parent_id=parent.id,
                event_key=event_key,
            )
            await broadcast_service.increment_delivered(bid, db)
            delivered += 1
        except Exception:
            logger.exception(
                "Failed to deliver broadcast %s to parent %s",
                broadcast_id_str,
                parent.id,
            )
        # Rate-limit: 200ms between sends to avoid WhatsApp throttling
        time.sleep(0.2)

    await broadcast_service.mark_sent(bid, db)
    logger.info(
        "Broadcast %s complete: %d/%d delivered",
        broadcast_id_str,
        delivered,
        len(parents),
    )
    return {"delivered": delivered, "total": len(parents)}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def fan_out_permission_slip(self, slip_id: str) -> dict:
    from app.database import async_session_factory

    async def _process():
        async with async_session_factory() as db:
            try:
                result = await _send_permission_slip(slip_id, db)
                await db.commit()
                return result
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.exception("Permission slip fan-out failed for %s", slip_id)
        raise self.retry(exc=exc)


async def _send_permission_slip(slip_id_str: str, db) -> dict:
    from app.services import broadcast_service, permission_service
    from app.services.notification_service import send_notification

    sid = uuid.UUID(slip_id_str)
    slip = await permission_service.get_slip(sid, db)
    if not slip:
        logger.error("Permission slip %s not found", slip_id_str)
        return {"error": "not_found"}

    parents = await broadcast_service.resolve_recipients(
        slip.segment_type, slip.segment_value, db
    )

    sent = 0
    for parent in parents:
        event_key = f"slip_push:{slip_id_str}:{parent.id}"
        try:
            date_line = f"\nEvent: {slip.event_date.strftime('%d/%m/%Y')}" if slip.event_date else ""
            if slip.description:
                body = (
                    f"Consent Required: {slip.title}\n\n{slip.description}"
                    f"{date_line}\n\nReply 'menu' to respond."
                )
            else:
                body = (
                    f"Consent Required: {slip.title}"
                    f"{date_line}\n\n"
                    f"Please message us to respond. Reply 'menu' to open the app."
                )

            await send_notification(
                recipient_whatsapp=parent.whatsapp_number,
                notification_type="permission_slip",
                message_body=body,
                db=db,
                parent_id=parent.id,
                event_key=event_key,
            )
            sent += 1
        except Exception:
            logger.exception("Failed to push slip %s to parent %s", slip_id_str, parent.id)
        time.sleep(0.2)

    logger.info("Permission slip %s pushed to %d/%d parents", slip_id_str, sent, len(parents))
    return {"sent": sent, "total": len(parents)}
