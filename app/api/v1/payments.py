import logging
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.payment import PaymentListOut, PaymentOut, PaymentVerifyOut
from app.services import billing_service, payment_service
from app.utils.auth import get_current_user
from app.utils.receipt import send_invoice_payment_receipt, send_payment_receipt
from app.utils.signature_verify import verify_paystack_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/webhook/paystack")
async def paystack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    if not verify_paystack_signature(
        body, signature, settings.PAYSTACK_SECRET_KEY
    ):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = await request.json()
    event = payload.get("event", "")

    if event == "charge.success":
        payment = await payment_service.process_webhook_event(payload, db)
        if payment and payment.status == "paid":
            if payment.invoice_id:
                await billing_service.process_invoice_payment(payment, db)
                await send_invoice_payment_receipt(payment, db)
            else:
                await send_payment_receipt(payment, db)
    else:
        logger.info("Ignoring Paystack event: %s", event)

    return {"status": "ok"}


@router.get("/", response_model=list[PaymentListOut])
async def list_payments(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentListOut]:
    payments = await payment_service.get_all_payments(
        db, status=status, limit=limit, offset=offset
    )
    return [PaymentListOut.model_validate(p) for p in payments]


@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: uuid.UUID,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentOut:
    payment = await payment_service.get_payment_by_id(payment_id, db)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentOut.model_validate(payment)


@router.get("/student/{student_id}", response_model=list[PaymentListOut])
async def list_student_payments(
    student_id: uuid.UUID,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentListOut]:
    payments = await payment_service.get_payments_for_student(student_id, db)
    return [PaymentListOut.model_validate(p) for p in payments]


@router.get("/verify/{reference}", response_model=PaymentVerifyOut)
async def verify_payment(
    reference: str,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentVerifyOut:
    payment = await payment_service.get_payment_by_reference(reference, db)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    try:
        paystack_data = await payment_service.verify_paystack_transaction(
            reference, db
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return PaymentVerifyOut(
        reference=reference,
        status=payment.status,
        amount=payment.amount,
        paystack_status=paystack_data.get("status", "unknown"),
        verified=paystack_data.get("status") == "success",
    )
