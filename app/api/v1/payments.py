import logging
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.rate_limit import limiter
from app.models.admin_user import AdminUser
from app.schemas.payment import PaymentListOut, PaymentOut, PaymentVerifyOut
from app.services import admin_notify, billing_service, payment_service
from app.utils.auth import require_role
from app.utils.receipt import send_invoice_payment_receipt, send_payment_receipt
from app.utils.signature_verify import verify_paystack_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])

_CALLBACK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EduConnect AI — Payment</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
min-height:100vh;display:flex;align-items:center;justify-content:center;
background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);color:#f1f5f9;padding:24px}}
.card{{background:#1e293b;border-radius:16px;padding:40px 32px;max-width:420px;
width:100%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.4)}}
.icon{{font-size:56px;margin-bottom:16px}}
h1{{font-size:22px;font-weight:600;margin-bottom:8px}}
.ref{{font-size:13px;color:#94a3b8;margin-bottom:24px;word-break:break-all}}
.amount{{font-size:32px;font-weight:700;color:#34d399;margin-bottom:24px}}
.amount.failed{{color:#f87171}}
p{{font-size:15px;line-height:1.6;color:#cbd5e1;margin-bottom:24px}}
.btn{{display:inline-block;padding:12px 28px;border-radius:8px;
background:#2563eb;color:#fff;text-decoration:none;font-weight:500;font-size:15px}}
.btn:hover{{background:#1d4ed8}}
</style>
</head>
<body>
<div class="card">
<div class="icon">{icon}</div>
<h1>{title}</h1>
<div class="ref">{ref_line}</div>
{amount_block}
<p>{message}</p>
<a class="btn" href="https://wa.me/?text=menu">Return to Chat</a>
</div>
</body>
</html>"""


@router.get("/callback")
async def payment_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    reference = request.query_params.get("reference") or request.query_params.get("trxref", "")

    if not reference:
        html = _CALLBACK_HTML.format(
            icon="⚠️",
            title="Missing Reference",
            ref_line="",
            amount_block="",
            message="No payment reference was provided. Please return to the chat and try again.",
        )
        return HTMLResponse(html, status_code=400)

    payment = await payment_service.get_payment_by_reference(reference, db)

    if not payment:
        html = _CALLBACK_HTML.format(
            icon="❌",
            title="Payment Not Found",
            ref_line=f"Reference: {reference}",
            amount_block="",
            message="We could not find this payment. If you believe this is an error, please contact support.",
        )
        return HTMLResponse(html, status_code=404)

    if payment.status != "paid":
        try:
            paystack_data = await payment_service.verify_paystack_transaction(
                reference, db
            )
            if paystack_data.get("status") == "success":
                await db.refresh(payment)

            if payment.status == "paid":
                if payment.invoice_id:
                    await billing_service.process_invoice_payment(payment, db)
                    await send_invoice_payment_receipt(payment, db)
                else:
                    await send_payment_receipt(payment, db)
                await db.commit()
        except Exception:
            logger.exception("Callback verification failed for %s", reference)

    if payment.status == "paid":
        html = _CALLBACK_HTML.format(
            icon="✅",
            title="Payment Successful!",
            ref_line=f"Reference: {payment.reference}",
            amount_block=f'<div class="amount">N{payment.amount:,.0f}</div>',
            message="Your payment has been confirmed. A receipt has been sent to your chat. You can close this page.",
        )
        return HTMLResponse(html)

    html = _CALLBACK_HTML.format(
        icon="⏳",
        title="Payment Pending",
        ref_line=f"Reference: {payment.reference}",
        amount_block=f'<div class="amount failed">N{payment.amount:,.0f}</div>',
        message="Your payment is still being processed. You will receive a confirmation in your chat once it completes.",
    )
    return HTMLResponse(html)


# Paystack events that mean money went back out. None of them adjust an
# invoice automatically — reversing a credit has accounting consequences a
# human should decide on — so they raise an alert instead.
REFUND_EVENTS = frozenset({
    "charge.refunded",
    "refund.processed",
    "refund.failed",
    "refund.pending",
    "charge.dispute.create",
    "charge.dispute.remind",
})


async def _handle_refund_event(
    event: str, payload: dict, db: AsyncSession
) -> None:
    data = payload.get("data", {}) or {}
    reference = (
        data.get("reference")
        or (data.get("transaction") or {}).get("reference")
        or ""
    )

    amount_raw = data.get("amount")
    try:
        amount = f"{Decimal(str(amount_raw)) / 100:,.2f}" if amount_raw else "unknown"
    except Exception:
        amount = "unknown"

    invoice_number = None
    parent_name = None
    if reference:
        payment = await payment_service.get_payment_by_reference(reference, db)
        if payment and payment.invoice_id:
            invoice = await billing_service.get_invoice(payment.invoice_id, db)
            if invoice:
                invoice_number = invoice.invoice_number

    logger.warning(
        "Paystack %s received for reference %s — invoice NOT adjusted automatically",
        event, reference or "(none)",
    )
    await admin_notify.notify_refund(
        reference=reference or "(none)",
        event=event,
        amount=amount,
        invoice_number=invoice_number,
        parent_name=parent_name,
    )


@router.post("/webhook/paystack")
@limiter.limit("20/minute")
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
        reference = payload.get("data", {}).get("reference", "")
        existing = await payment_service.get_payment_by_reference(reference, db) if reference else None
        already_paid = existing and existing.status == "paid"

        payment = await payment_service.process_webhook_event(payload, db)
        if payment and payment.status == "paid" and not already_paid:
            if payment.invoice_id:
                await billing_service.process_invoice_payment(payment, db)
                await send_invoice_payment_receipt(payment, db)
            else:
                await send_payment_receipt(payment, db)
            await db.commit()
        elif already_paid:
            logger.info("Duplicate webhook for already-paid reference: %s", reference)
    elif event in REFUND_EVENTS:
        await _handle_refund_event(event, payload, db)
    else:
        logger.info("Ignoring Paystack event: %s", event)

    return {"status": "ok"}


@router.get("/", response_model=list[PaymentListOut])
async def list_payments(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentListOut]:
    payments = await payment_service.get_all_payments(
        db, status=status, limit=limit, offset=offset
    )
    return [PaymentListOut.model_validate(p) for p in payments]


@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: uuid.UUID,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> PaymentOut:
    payment = await payment_service.get_payment_by_id(payment_id, db)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentOut.model_validate(payment)


@router.get("/student/{student_id}", response_model=list[PaymentListOut])
async def list_student_payments(
    student_id: uuid.UUID,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentListOut]:
    payments = await payment_service.get_payments_for_student(student_id, db)
    return [PaymentListOut.model_validate(p) for p in payments]


@router.get("/verify/{reference}", response_model=PaymentVerifyOut)
async def verify_payment(
    reference: str,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
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
