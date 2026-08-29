from fastapi import APIRouter

from app.api.v1 import admin, analytics, auth, billing, broadcast, calendar, engagement, notifications, payments, payment_plan, permission, programmes, report_cards, students, telegram, whatsapp

router = APIRouter(prefix="/api/v1")
router.include_router(whatsapp.router)
router.include_router(telegram.router)
router.include_router(programmes.router)
router.include_router(students.router)
router.include_router(payments.router)
router.include_router(billing.router)
router.include_router(payment_plan.router)
router.include_router(broadcast.router)
router.include_router(calendar.router)
router.include_router(permission.router)
router.include_router(report_cards.router)
router.include_router(notifications.router)
router.include_router(auth.router)
router.include_router(admin.router)
router.include_router(analytics.router)
router.include_router(engagement.router)
