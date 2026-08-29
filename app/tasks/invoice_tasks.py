import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

WAT = timezone(timedelta(hours=1))

REMINDER_SCHEDULE = [
    {"days_before": 7, "urgency": "friendly", "label": "7-day"},
    {"days_before": 3, "urgency": "reminder", "label": "3-day"},
    {"days_before": 0, "urgency": "urgent", "label": "due-today"},
    {"days_before": -1, "urgency": "overdue", "label": "1-day-overdue"},
    {"days_before": -3, "urgency": "overdue", "label": "3-day-overdue"},
    {"days_before": -7, "urgency": "overdue", "label": "7-day-overdue"},
    {"days_before": -14, "urgency": "final", "label": "14-day-overdue"},
]


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def send_invoice_reminders(self) -> dict:
    from app.database import async_session_factory

    async def _process():
        async with async_session_factory() as db:
            try:
                count = await _send_invoice_reminders(db)
                await db.commit()
                return {"sent": count}
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.exception("Invoice reminder task failed")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def check_overdue_invoices(self) -> dict:
    from app.database import async_session_factory

    async def _process():
        async with async_session_factory() as db:
            try:
                from app.services import billing_service
                count = await billing_service.check_overdue_invoices(db)
                await db.commit()
                return {"marked_overdue": count}
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.exception("Overdue invoice check failed")
        raise self.retry(exc=exc)


async def _send_invoice_reminders(db: AsyncSession) -> int:
    from app.models.invoice import Invoice
    from app.models.parent import Parent
    from app.models.student import Student
    from app.services.notification_service import (
        TEMPLATE_INVOICE_REMINDER,
        send_notification,
    )

    today = datetime.now(WAT).date()

    result = await db.execute(
        select(Invoice).where(
            Invoice.status.in_(["unpaid", "partial", "overdue"]),
            Invoice.due_date != None,  # noqa: E711
        )
    )
    invoices = list(result.scalars().all())

    if not invoices:
        logger.info("No outstanding invoices with due dates")
        return 0

    sent_count = 0

    for invoice in invoices:
        days_until_due = (invoice.due_date - today).days

        matched_tier = None
        for tier in REMINDER_SCHEDULE:
            if days_until_due == tier["days_before"]:
                matched_tier = tier
                break

        if not matched_tier:
            continue

        parent_result = await db.execute(
            select(Parent).where(Parent.id == invoice.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            continue

        student_name = None
        if invoice.student_id:
            student_result = await db.execute(
                select(Student).where(Student.id == invoice.student_id)
            )
            student = student_result.scalar_one_or_none()
            student_name = student.full_name if student else None

        remaining = invoice.total_amount - invoice.amount_paid
        event_key = (
            f"invoice_reminder:{invoice.id}:{matched_tier['label']}:{today}"
        )

        message = _build_reminder_message(
            parent_name=parent.full_name or "Parent",
            student_name=student_name,
            invoice=invoice,
            remaining=remaining,
            urgency=matched_tier["urgency"],
            days_until_due=days_until_due,
        )

        await send_notification(
            recipient_whatsapp=parent.whatsapp_number,
            notification_type="invoice_reminder",
            message_body=message,
            db=db,
            parent_id=parent.id,
            student_id=invoice.student_id,
            event_key=event_key,
            template_name=TEMPLATE_INVOICE_REMINDER,
            template_params=[
                parent.full_name or "Parent",
                invoice.title,
                f"N{remaining:,.0f}",
                invoice.due_date.strftime("%d/%m/%Y"),
            ],
        )
        sent_count += 1

    logger.info("Invoice reminders: %d sent", sent_count)
    return sent_count


def _build_reminder_message(
    parent_name: str,
    student_name: str | None,
    invoice,
    remaining,
    urgency: str,
    days_until_due: int,
) -> str:
    student_line = f"\nStudent: {student_name}" if student_name else ""
    due_str = invoice.due_date.strftime("%d/%m/%Y")

    if urgency == "friendly":
        return (
            f"Hi {parent_name},\n\n"
            f"This is a friendly reminder that the following fee "
            f"is due on {due_str}:\n\n"
            f"Invoice: {invoice.invoice_number}\n"
            f"{invoice.title}{student_line}\n"
            f"Amount Due: N{remaining:,.0f}\n\n"
            f"Reply 'menu' and select 'Make Payment' to pay now."
        )

    if urgency == "reminder":
        return (
            f"Hi {parent_name},\n\n"
            f"Payment reminder: your invoice is due in 3 days "
            f"({due_str}).\n\n"
            f"Invoice: {invoice.invoice_number}\n"
            f"{invoice.title}{student_line}\n"
            f"Amount Due: N{remaining:,.0f}\n\n"
            f"Reply 'menu' and select 'Make Payment' to pay now."
        )

    if urgency == "urgent":
        return (
            f"Hi {parent_name},\n\n"
            f"Your payment is due TODAY.\n\n"
            f"Invoice: {invoice.invoice_number}\n"
            f"{invoice.title}{student_line}\n"
            f"Amount Due: N{remaining:,.0f}\n\n"
            f"Please make your payment today to avoid late fees. "
            f"Reply 'menu' and select 'Make Payment'."
        )

    if urgency == "final":
        days_overdue = abs(days_until_due)
        return (
            f"Hi {parent_name},\n\n"
            f"FINAL NOTICE: Your payment is {days_overdue} days overdue.\n\n"
            f"Invoice: {invoice.invoice_number}\n"
            f"{invoice.title}{student_line}\n"
            f"Amount Due: N{remaining:,.0f}\n"
            f"Due Date: {due_str}\n\n"
            f"Please settle this immediately to avoid further action. "
            f"Reply 'menu' and select 'Make Payment', or contact "
            f"support if you need assistance."
        )

    days_overdue = abs(days_until_due)
    return (
        f"Hi {parent_name},\n\n"
        f"Your payment is {days_overdue} day(s) overdue.\n\n"
        f"Invoice: {invoice.invoice_number}\n"
        f"{invoice.title}{student_line}\n"
        f"Amount Due: N{remaining:,.0f}\n"
        f"Due Date: {due_str}\n\n"
        f"Please pay as soon as possible. "
        f"Reply 'menu' and select 'Make Payment'."
    )
