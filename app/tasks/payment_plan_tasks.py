import asyncio
import logging
from datetime import date, timedelta, timezone, datetime

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def send_installment_reminders(self) -> dict:
    from app.database import async_session_factory

    async def _process():
        async with async_session_factory() as db:
            try:
                count = await _send_reminders(db)
                await db.commit()
                return {"sent": count}
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.exception("Installment reminder task failed")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def check_overdue_installments(self) -> dict:
    from app.database import async_session_factory

    async def _process():
        async with async_session_factory() as db:
            try:
                from app.services import payment_plan_service
                count = await payment_plan_service.check_and_mark_overdue(db)
                await db.commit()
                return {"marked_overdue": count}
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.exception("Overdue installment check failed")
        raise self.retry(exc=exc)


async def _send_reminders(db) -> int:
    from sqlalchemy import select
    from app.models.payment_plan import PaymentPlan, PaymentPlanInstallment
    from app.models.parent import Parent
    from app.services.notification_service import send_notification

    tomorrow = date.today() + timedelta(days=1)
    today_str = date.today().isoformat()

    result = await db.execute(
        select(PaymentPlanInstallment).where(
            PaymentPlanInstallment.due_date == tomorrow,
            PaymentPlanInstallment.status == "pending",
        )
    )
    installments = list(result.scalars().all())

    sent = 0
    for inst in installments:
        plan_result = await db.execute(
            select(PaymentPlan).where(PaymentPlan.id == inst.plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        if not plan or plan.status != "active":
            continue

        parent_result = await db.execute(
            select(Parent).where(Parent.id == plan.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            continue

        due_str = inst.due_date.strftime("%d/%m/%Y")
        body = (
            f"Hi {parent.full_name or 'Parent'},\n\n"
            f"Reminder: installment #{inst.installment_number} of your payment plan is due tomorrow ({due_str}).\n\n"
            f"Amount: N{inst.amount:,.0f}\n\n"
            f"Reply 'menu' to view your balance."
        )

        event_key = f"installment_reminder:{inst.id}:{today_str}"
        try:
            await send_notification(
                recipient_whatsapp=parent.whatsapp_number,
                notification_type="installment_reminder",
                message_body=body,
                db=db,
                parent_id=parent.id,
                event_key=event_key,
            )
            sent += 1
        except Exception:
            logger.exception("Failed to send installment reminder to %s", parent.whatsapp_number)

    logger.info("Installment reminders sent: %d", sent)
    return sent
