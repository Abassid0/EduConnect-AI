import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

WAT = timezone(timedelta(hours=1))


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def send_class_reminders_24h(self) -> dict:
    from app.database import async_session_factory

    async def _process():
        async with async_session_factory() as db:
            try:
                count = await _send_class_reminders(db, hours_before=24)
                await db.commit()
                return {"sent": count}
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.exception("Class reminder (24h) task failed")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def send_class_reminders_1h(self) -> dict:
    from app.database import async_session_factory

    async def _process():
        async with async_session_factory() as db:
            try:
                count = await _send_class_reminders(db, hours_before=1)
                await db.commit()
                return {"sent": count}
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.exception("Class reminder (1h) task failed")
        raise self.retry(exc=exc)


async def _send_class_reminders(db: AsyncSession, hours_before: int) -> int:
    from app.models.class_schedule import ClassSchedule
    from app.models.enrollment import Enrollment
    from app.models.parent import Parent
    from app.models.programme import Programme
    from app.models.student import Student
    from app.services.notification_service import (
        TEMPLATE_CLASS_REMINDER_1H,
        TEMPLATE_CLASS_REMINDER_24H,
        send_notification,
    )

    now_wat = datetime.now(WAT)

    if hours_before == 24:
        target_date = (now_wat + timedelta(days=1)).date()
        template = TEMPLATE_CLASS_REMINDER_24H
        notif_type = "class_reminder_24h"
        time_label = "tomorrow"
    else:
        target_date = now_wat.date()
        template = TEMPLATE_CLASS_REMINDER_1H
        notif_type = "class_reminder_1h"
        time_label = "in 1 hour"

    target_day_of_week = target_date.weekday()

    result = await db.execute(
        select(ClassSchedule).where(
            ClassSchedule.day_of_week == target_day_of_week
        )
    )
    schedules = list(result.scalars().all())

    if not schedules:
        logger.info("No classes on day %d, nothing to remind", target_day_of_week)
        return 0

    if hours_before == 1:
        window_start = (now_wat + timedelta(minutes=50)).time()
        window_end = (now_wat + timedelta(minutes=70)).time()
        schedules = [
            s for s in schedules
            if s.start_time and window_start <= s.start_time <= window_end
        ]
        if not schedules:
            return 0

    sent_count = 0

    for schedule in schedules:
        programme_result = await db.execute(
            select(Programme).where(Programme.id == schedule.programme_id)
        )
        programme = programme_result.scalar_one_or_none()
        if not programme or not programme.is_active:
            continue

        enrollment_result = await db.execute(
            select(Enrollment).where(
                Enrollment.programme_id == programme.id,
                Enrollment.status.in_(["confirmed", "pending"]),
            )
        )
        enrollments = list(enrollment_result.scalars().all())

        for enrollment in enrollments:
            if enrollment.schedule_id and enrollment.schedule_id != schedule.id:
                continue

            student_result = await db.execute(
                select(Student).where(Student.id == enrollment.student_id)
            )
            student = student_result.scalar_one_or_none()
            if not student:
                continue

            parent_result = await db.execute(
                select(Parent).where(Parent.id == student.parent_id)
            )
            parent = parent_result.scalar_one_or_none()
            if not parent:
                continue

            event_key = (
                f"{notif_type}:{student.id}:{schedule.id}:{target_date}"
            )

            start_str = (
                schedule.start_time.strftime("%I:%M %p")
                if schedule.start_time
                else "TBD"
            )
            message = (
                f"Reminder: {student.full_name} has "
                f"{programme.name} {time_label}!\n\n"
                f"Day: {schedule.day_name}\n"
                f"Time: {start_str}\n"
                f"Mode: {programme.delivery_mode or 'N/A'}\n\n"
                f"See you there!"
            )

            await send_notification(
                recipient_whatsapp=parent.whatsapp_number,
                notification_type=notif_type,
                message_body=message,
                db=db,
                parent_id=parent.id,
                student_id=student.id,
                event_key=event_key,
                template_name=template,
                template_params=[
                    student.full_name,
                    programme.name,
                    start_str,
                ],
            )
            sent_count += 1

    logger.info("Class reminders (%s): %d sent", notif_type, sent_count)
    return sent_count


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def send_payment_reminders(self) -> dict:
    from app.database import async_session_factory

    async def _process():
        async with async_session_factory() as db:
            try:
                count = await _send_payment_reminders(db)
                await db.commit()
                return {"sent": count}
            except Exception:
                await db.rollback()
                raise

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.exception("Payment reminder task failed")
        raise self.retry(exc=exc)


async def _send_payment_reminders(db: AsyncSession) -> int:
    from app.models.enrollment import Enrollment
    from app.models.parent import Parent
    from app.models.payment import Payment
    from app.models.programme import Programme
    from app.models.student import Student
    from app.services.notification_service import (
        TEMPLATE_PAYMENT_REMINDER_7DAY,
        TEMPLATE_PAYMENT_REMINDER_DUE,
        TEMPLATE_PAYMENT_REMINDER_OVERDUE,
        send_notification,
    )

    now_wat = datetime.now(WAT)
    today = now_wat.date()

    enrollment_result = await db.execute(
        select(Enrollment).where(Enrollment.status == "pending")
    )
    pending_enrollments = list(enrollment_result.scalars().all())

    sent_count = 0

    for enrollment in pending_enrollments:
        paid_result = await db.execute(
            select(Payment).where(
                Payment.enrollment_id == enrollment.id,
                Payment.status.in_(["paid", "pending"]),
            ).limit(1)
        )
        if paid_result.scalar_one_or_none():
            continue

        student_result = await db.execute(
            select(Student).where(Student.id == enrollment.student_id)
        )
        student = student_result.scalar_one_or_none()
        if not student:
            continue

        parent_result = await db.execute(
            select(Parent).where(Parent.id == student.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            continue

        programme_result = await db.execute(
            select(Programme).where(Programme.id == enrollment.programme_id)
        )
        programme = programme_result.scalar_one_or_none()
        if not programme:
            continue

        enrolled_date = (
            enrollment.enrolled_at.date()
            if enrollment.enrolled_at
            else enrollment.created_at.date()
        )
        due_date = enrolled_date + timedelta(days=7)
        days_until_due = (due_date - today).days

        template = None
        notif_type = None
        urgency = None

        if days_until_due == 7:
            template = TEMPLATE_PAYMENT_REMINDER_7DAY
            notif_type = "payment_reminder_7day"
            urgency = "friendly"
        elif days_until_due == 0:
            template = TEMPLATE_PAYMENT_REMINDER_DUE
            notif_type = "payment_reminder_due"
            urgency = "urgent"
        elif days_until_due == -1:
            template = TEMPLATE_PAYMENT_REMINDER_OVERDUE
            notif_type = "payment_reminder_overdue"
            urgency = "overdue"
        else:
            continue

        event_key = f"{notif_type}:{enrollment.id}:{today}"
        fee_str = f"N{programme.fee:,.0f}"

        if urgency == "friendly":
            message = (
                f"Hi {parent.full_name or 'there'},\n\n"
                f"Just a friendly reminder that payment for "
                f"{student.full_name}'s enrollment in "
                f"{programme.name} is due on "
                f"{due_date.strftime('%d/%m/%Y')}.\n\n"
                f"Amount: {fee_str}\n\n"
                f"Reply 'menu' and select 'Make Payment' to pay now."
            )
        elif urgency == "urgent":
            message = (
                f"Hi {parent.full_name or 'there'},\n\n"
                f"Payment for {student.full_name}'s enrollment in "
                f"{programme.name} is due today.\n\n"
                f"Amount: {fee_str}\n\n"
                f"Please make your payment to secure the spot. "
                f"Reply 'menu' and select 'Make Payment'."
            )
        else:
            message = (
                f"Hi {parent.full_name or 'there'},\n\n"
                f"Payment for {student.full_name}'s enrollment in "
                f"{programme.name} is now overdue.\n\n"
                f"Amount: {fee_str}\n\n"
                f"Please pay as soon as possible to avoid losing "
                f"the enrollment. Reply 'menu' and select "
                f"'Make Payment'."
            )

        await send_notification(
            recipient_whatsapp=parent.whatsapp_number,
            notification_type=notif_type,
            message_body=message,
            db=db,
            parent_id=parent.id,
            student_id=student.id,
            event_key=event_key,
            template_name=template,
            template_params=[
                parent.full_name or "Parent",
                student.full_name,
                programme.name,
                fee_str,
            ],
        )
        sent_count += 1

    logger.info("Payment reminders: %d sent", sent_count)
    return sent_count
