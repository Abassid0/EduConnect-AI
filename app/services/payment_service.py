import logging
import random
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.services import analytics_service

logger = logging.getLogger(__name__)

PAYSTACK_BASE_URL = "https://api.paystack.co"


def generate_payment_reference() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = random.randint(10000, 99999)
    return f"EDP-PAY-{ts}-{suffix}"


async def create_payment(
    student_id: uuid.UUID,
    enrollment_id: uuid.UUID,
    programme_id: uuid.UUID,
    amount: Decimal,
    currency: str,
    whatsapp_number: str,
    metadata: dict,
    db: AsyncSession,
) -> Payment:
    reference = generate_payment_reference()
    existing = await db.execute(
        select(Payment).where(Payment.reference == reference)
    )
    while existing.scalar_one_or_none() is not None:
        reference = generate_payment_reference()
        existing = await db.execute(
            select(Payment).where(Payment.reference == reference)
        )

    payment = Payment(
        id=uuid.uuid4(),
        reference=reference,
        student_id=student_id,
        enrollment_id=enrollment_id,
        programme_id=programme_id,
        amount=amount,
        currency=currency,
        whatsapp_number=whatsapp_number,
        status="pending",
        metadata_=metadata,
    )
    db.add(payment)
    await db.flush()
    return payment


async def initialize_paystack_transaction(
    payment: Payment,
    email: str | None,
    db: AsyncSession,
) -> Payment:
    if not email:
        email = f"{payment.whatsapp_number}@educonnect.ai"

    amount_kobo = int(payment.amount * 100)

    payload = {
        "email": email,
        "amount": amount_kobo,
        "reference": payment.reference,
        "currency": payment.currency,
        "callback_url": settings.PAYSTACK_CALLBACK_URL,
        "metadata": payment.metadata_,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
        )

    if response.status_code != 200:
        logger.error("Paystack init failed: %s %s", response.status_code, response.text)
        payment.status = "failed"
        await db.flush()
        raise RuntimeError(f"Paystack initialization failed: {response.text}")

    data = response.json().get("data", {})
    payment.paystack_reference = data.get("reference")
    payment.paystack_authorization_url = data.get("authorization_url")
    await db.flush()
    return payment


async def process_webhook_event(
    event_data: dict,
    db: AsyncSession,
) -> Payment | None:
    reference = event_data.get("data", {}).get("reference")
    if not reference:
        logger.warning("Paystack webhook missing reference")
        return None

    result = await db.execute(
        select(Payment)
        .where(Payment.reference == reference)
        .with_for_update()
    )
    payment = result.scalar_one_or_none()

    if not payment:
        logger.warning("Payment not found for reference: %s", reference)
        return None

    if payment.status == "paid":
        return payment

    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)
    payment.metadata_ = {
        **payment.metadata_,
        "paystack_transaction_id": event_data.get("data", {}).get("id"),
        "paystack_channel": event_data.get("data", {}).get("channel"),
    }

    if payment.enrollment_id:
        result = await db.execute(
            select(Enrollment)
            .where(Enrollment.id == payment.enrollment_id)
            .with_for_update()
        )
        enrollment = result.scalar_one_or_none()
        if enrollment:
            enrollment.status = "confirmed"

    await db.flush()

    await analytics_service.track_event(
        "payment_complete",
        db,
        whatsapp_number=payment.whatsapp_number,
        student_id=payment.student_id,
        properties={
            "amount": str(payment.amount),
            "reference": payment.reference,
            "channel": event_data.get("data", {}).get("channel"),
        },
    )

    return payment


async def verify_paystack_transaction(
    reference: str,
    db: AsyncSession,
) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers={
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            },
        )

    if response.status_code != 200:
        raise RuntimeError(f"Paystack verification failed: {response.text}")

    paystack_data = response.json().get("data", {})

    if paystack_data.get("status") == "success":
        result = await db.execute(
            select(Payment)
            .where(Payment.reference == reference)
            .with_for_update()
        )
        payment = result.scalar_one_or_none()
        if payment and payment.status == "pending":
            payment.status = "paid"
            payment.paid_at = datetime.now(timezone.utc)

            if payment.enrollment_id:
                enr_result = await db.execute(
                    select(Enrollment)
                    .where(Enrollment.id == payment.enrollment_id)
                    .with_for_update()
                )
                enrollment = enr_result.scalar_one_or_none()
                if enrollment:
                    enrollment.status = "confirmed"

            await db.flush()

    return paystack_data


async def get_payment_by_reference(
    reference: str, db: AsyncSession
) -> Payment | None:
    result = await db.execute(
        select(Payment).where(Payment.reference == reference)
    )
    return result.scalar_one_or_none()


async def get_payment_by_id(
    payment_id: uuid.UUID, db: AsyncSession
) -> Payment | None:
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    return result.scalar_one_or_none()


async def get_payments_for_student(
    student_id: uuid.UUID, db: AsyncSession
) -> list[Payment]:
    result = await db.execute(
        select(Payment)
        .where(Payment.student_id == student_id)
        .order_by(Payment.created_at.desc())
    )
    return list(result.scalars().all())


async def get_pending_enrollments(
    student_id: uuid.UUID, db: AsyncSession
) -> list[Enrollment]:
    paid_enrollment_ids = (
        select(Payment.enrollment_id)
        .where(
            Payment.student_id == student_id,
            Payment.status.in_(["pending", "paid"]),
        )
        .scalar_subquery()
    )
    result = await db.execute(
        select(Enrollment)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status == "pending",
            Enrollment.id.notin_(paid_enrollment_ids),
        )
        .order_by(Enrollment.created_at.desc())
    )
    return list(result.scalars().all())


async def get_payments_for_student_list(
    student_ids: list[uuid.UUID], db: AsyncSession
) -> list[Payment]:
    if not student_ids:
        return []
    result = await db.execute(
        select(Payment)
        .where(Payment.student_id.in_(student_ids))
        .order_by(Payment.created_at.desc())
    )
    return list(result.scalars().all())


async def get_all_payments(
    db: AsyncSession,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Payment]:
    query = select(Payment).order_by(Payment.created_at.desc())
    if status:
        query = query.where(Payment.status == status)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())
