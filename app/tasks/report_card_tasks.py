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
def fan_out_report_card(self, report_card_id: str) -> dict:
    from app.database import async_session_factory

    async def _process():
        async with async_session_factory() as db:
            try:
                result = await _send_report_card(report_card_id, db)
                await db.commit()
                return result
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.exception("Report card fan-out failed for %s", report_card_id)
        raise self.retry(exc=exc)


async def _send_report_card(report_card_id_str: str, db) -> dict:
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models.report_card import ReportCard, ReportCardDelivery
    from app.models.parent import Parent
    from app.models.student import Student
    from app.services import report_card_service
    from app.services.notification_service import send_notification

    rc_id = uuid.UUID(report_card_id_str)
    card = await report_card_service.get_report_card(rc_id, db)
    if not card:
        logger.error("Report card %s not found", report_card_id_str)
        return {"error": "not_found"}

    student_result = await db.execute(select(Student).where(Student.id == card.student_id))
    student = student_result.scalar_one_or_none()
    student_name = student.full_name if student else ""

    message_body = report_card_service.format_report_card_message(card, student_name)

    deliveries_result = await db.execute(
        select(ReportCardDelivery).where(ReportCardDelivery.report_card_id == rc_id)
    )
    deliveries = list(deliveries_result.scalars().all())

    sent = 0
    for delivery in deliveries:
        parent_result = await db.execute(select(Parent).where(Parent.id == delivery.parent_id))
        parent = parent_result.scalar_one_or_none()
        if not parent:
            continue

        event_key = f"rc_delivery:{report_card_id_str}:{parent.id}"
        try:
            await send_notification(
                recipient_whatsapp=parent.whatsapp_number,
                notification_type="report_card",
                message_body=message_body,
                db=db,
                parent_id=parent.id,
                event_key=event_key,
            )
            delivery.delivered_at = datetime.now(timezone.utc)
            sent += 1
        except Exception:
            logger.exception("Failed to send report card to %s", parent.whatsapp_number)

        time.sleep(0.2)

    await db.flush()
    logger.info("Report card %s delivered to %d parents", report_card_id_str, sent)
    return {"delivered": sent, "total": len(deliveries)}
