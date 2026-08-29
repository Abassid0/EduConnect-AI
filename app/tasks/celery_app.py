from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "edpassare",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.webhook_tasks",
        "app.tasks.reminder_tasks",
        "app.tasks.invoice_tasks",
        "app.tasks.broadcast_tasks",
        "app.tasks.payment_plan_tasks",
        "app.tasks.report_card_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Lagos",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    "class-reminders-24h": {
        "task": "app.tasks.reminder_tasks.send_class_reminders_24h",
        "schedule": crontab(hour=7, minute=0),
    },
    "class-reminders-1h": {
        "task": "app.tasks.reminder_tasks.send_class_reminders_1h",
        "schedule": crontab(minute="*/10"),
    },
    "payment-reminders-daily": {
        "task": "app.tasks.reminder_tasks.send_payment_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    "invoice-reminders-daily": {
        "task": "app.tasks.invoice_tasks.send_invoice_reminders",
        "schedule": crontab(hour=8, minute=30),
    },
    "check-overdue-invoices": {
        "task": "app.tasks.invoice_tasks.check_overdue_invoices",
        "schedule": crontab(hour=0, minute=15),
    },
    "installment-reminders-daily": {
        "task": "app.tasks.payment_plan_tasks.send_installment_reminders",
        "schedule": crontab(hour=8, minute=45),
    },
    "check-overdue-installments": {
        "task": "app.tasks.payment_plan_tasks.check_overdue_installments",
        "schedule": crontab(hour=0, minute=30),
    },
}

celery_app.autodiscover_tasks(["app.tasks"])
