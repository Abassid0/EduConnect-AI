import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationPreference
from app.models.parent import Parent
from app.services.whatsapp_service import wa_service

logger = logging.getLogger(__name__)

WAT = timezone(timedelta(hours=1))

TEMPLATE_CLASS_REMINDER_24H = "class_reminder_24h"
TEMPLATE_CLASS_REMINDER_1H = "class_reminder_1h"
TEMPLATE_PAYMENT_REMINDER_7DAY = "payment_reminder_7day"
TEMPLATE_PAYMENT_REMINDER_DUE = "payment_reminder_due"
TEMPLATE_PAYMENT_REMINDER_OVERDUE = "payment_reminder_overdue"
TEMPLATE_INVOICE_NOTIFICATION = "invoice_notification"
TEMPLATE_INVOICE_REMINDER = "invoice_reminder"

PREF_MAP = {
    "class_reminder": "class_reminders",
    TEMPLATE_CLASS_REMINDER_24H: "class_reminders",
    TEMPLATE_CLASS_REMINDER_1H: "class_reminders",
    "payment_reminder": "payment_reminders",
    TEMPLATE_PAYMENT_REMINDER_7DAY: "payment_reminders",
    TEMPLATE_PAYMENT_REMINDER_DUE: "payment_reminders",
    TEMPLATE_PAYMENT_REMINDER_OVERDUE: "payment_reminders",
    "invoice_notification": "payment_reminders",
    "invoice_reminder": "payment_reminders",
    "marketing": "marketing",
    "event": "events",
    "progress_report": "progress_reports",
}

MAX_RETRY = 1


async def get_preferences(
    parent_id: uuid.UUID, db: AsyncSession
) -> NotificationPreference | None:
    result = await db.execute(
        select(NotificationPreference)
        .where(NotificationPreference.parent_id == parent_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_preferences(
    parent_id: uuid.UUID, db: AsyncSession
) -> NotificationPreference:
    prefs = await get_preferences(parent_id, db)
    if prefs is None:
        prefs = NotificationPreference(
            id=uuid.uuid4(),
            parent_id=parent_id,
        )
        db.add(prefs)
        await db.flush()
    return prefs


async def update_preferences(
    parent_id: uuid.UUID,
    updates: dict,
    db: AsyncSession,
) -> NotificationPreference:
    prefs = await get_or_create_preferences(parent_id, db)
    for key, value in updates.items():
        if hasattr(prefs, key) and isinstance(value, bool):
            setattr(prefs, key, value)
    await db.flush()
    await db.refresh(prefs)
    return prefs


async def check_preference(
    parent_id: uuid.UUID,
    notification_type: str,
    db: AsyncSession,
) -> bool:
    pref_field = PREF_MAP.get(notification_type)
    if not pref_field:
        return True

    prefs = await get_preferences(parent_id, db)
    if not prefs:
        return True

    return getattr(prefs, pref_field, True)


async def is_duplicate(
    notification_type: str,
    event_key: str,
    db: AsyncSession,
) -> bool:
    result = await db.execute(
        select(Notification)
        .where(
            Notification.notification_type == notification_type,
            Notification.event_key == event_key,
            Notification.status.in_(["sent", "pending"]),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def send_notification(
    recipient_whatsapp: str,
    notification_type: str,
    message_body: str,
    db: AsyncSession,
    parent_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    event_key: str | None = None,
    template_name: str | None = None,
    template_params: list[str] | None = None,
    metadata: dict | None = None,
    use_template: bool = False,
) -> Notification | None:
    if event_key and await is_duplicate(notification_type, event_key, db):
        logger.info(
            "Duplicate notification skipped: %s / %s",
            notification_type,
            event_key,
        )
        return None

    if parent_id:
        allowed = await check_preference(parent_id, notification_type, db)
        if not allowed:
            logger.info(
                "Notification blocked by preference: %s for parent %s",
                notification_type,
                parent_id,
            )
            return None

    notification = Notification(
        id=uuid.uuid4(),
        recipient_whatsapp=recipient_whatsapp,
        parent_id=parent_id,
        student_id=student_id,
        notification_type=notification_type,
        event_key=event_key,
        template_name=template_name,
        message_body=message_body,
        status="pending",
        scheduled_at=datetime.now(timezone.utc),
        metadata_=metadata or {},
    )
    db.add(notification)
    await db.flush()

    try:
        if use_template and template_name:
            await wa_service.send_template(
                recipient_whatsapp,
                template_name,
                params=template_params,
            )
        else:
            await wa_service.send_text(recipient_whatsapp, message_body)

        notification.status = "sent"
        notification.sent_at = datetime.now(timezone.utc)
        await db.flush()
        return notification

    except Exception as exc:
        logger.warning(
            "Notification send failed (attempt 1): %s — %s",
            notification.id,
            exc,
        )
        notification.retry_count = 1
        notification.error_message = str(exc)
        await db.flush()

        return await _retry_notification(notification, use_template, template_params, db)


async def _retry_notification(
    notification: Notification,
    use_template: bool,
    template_params: list[str] | None,
    db: AsyncSession,
) -> Notification | None:
    try:
        if use_template and notification.template_name:
            await wa_service.send_template(
                notification.recipient_whatsapp,
                notification.template_name,
                params=template_params,
            )
        else:
            await wa_service.send_text(
                notification.recipient_whatsapp,
                notification.message_body or "",
            )

        notification.status = "sent"
        notification.sent_at = datetime.now(timezone.utc)
        notification.error_message = None
        await db.flush()
        return notification

    except Exception as exc:
        logger.error(
            "Notification send failed (retry): %s — %s",
            notification.id,
            exc,
        )
        notification.status = "failed"
        notification.retry_count = 2
        notification.error_message = str(exc)
        await db.flush()

        await _create_support_event(notification, db)
        return notification


async def _create_support_event(
    notification: Notification, db: AsyncSession
) -> None:
    support_notif = Notification(
        id=uuid.uuid4(),
        recipient_whatsapp=notification.recipient_whatsapp,
        parent_id=notification.parent_id,
        student_id=notification.student_id,
        notification_type="support_alert",
        event_key=f"failed_{notification.id}",
        message_body=(
            f"We tried to send you a notification but it failed. "
            f"Please contact support if you're missing important updates. "
            f"Reference: {notification.id}"
        ),
        status="pending",
        metadata_={
            "original_notification_id": str(notification.id),
            "original_type": notification.notification_type,
            "failure_reason": notification.error_message,
        },
    )
    db.add(support_notif)

    try:
        await wa_service.send_text(
            notification.recipient_whatsapp,
            support_notif.message_body or "",
        )
        support_notif.status = "sent"
        support_notif.sent_at = datetime.now(timezone.utc)
    except Exception:
        support_notif.status = "failed"
        logger.exception(
            "Failed to send support event for notification %s",
            notification.id,
        )

    await db.flush()


async def get_notifications_for_parent(
    parent_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 20,
) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.parent_id == parent_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_all_notifications(
    db: AsyncSession,
    status: str | None = None,
    notification_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    query = select(Notification).order_by(Notification.created_at.desc())
    if status:
        query = query.where(Notification.status == status)
    if notification_type:
        query = query.where(Notification.notification_type == notification_type)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())
