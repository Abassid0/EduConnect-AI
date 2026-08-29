import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.payment import Payment
from app.services import programme_service
from app.services.whatsapp_service import wa_service

logger = logging.getLogger(__name__)


async def send_payment_receipt(payment: Payment, db: AsyncSession) -> None:
    programme = None
    if payment.programme_id:
        programme = await programme_service.get_programme_by_id(
            payment.programme_id, db
        )
    programme_name = programme.name if programme else "N/A"
    student_name = payment.student.full_name if payment.student else "N/A"

    paid_date = "N/A"
    if payment.paid_at:
        paid_date = payment.paid_at.strftime("%d/%m/%Y %H:%M")

    receipt_text = (
        "Payment Received!\n\n"
        f"Reference: {payment.reference}\n"
        f"Student: {student_name}\n"
        f"Programme: {programme_name}\n"
        f"Amount: N{payment.amount:,.0f} {payment.currency}\n"
        f"Date: {paid_date}\n"
        f"Status: Confirmed\n\n"
        "Your enrollment has been confirmed. Thank you!"
    )

    try:
        await wa_service.send_text(payment.whatsapp_number, receipt_text)
    except Exception:
        logger.exception(
            "Failed to send receipt for payment %s", payment.reference
        )


async def send_invoice_payment_receipt(payment: Payment, db: AsyncSession) -> None:
    result = await db.execute(
        select(Invoice).where(Invoice.id == payment.invoice_id)
    )
    invoice = result.scalar_one_or_none()

    invoice_number = invoice.invoice_number if invoice else "N/A"
    invoice_title = invoice.title if invoice else payment.description or "N/A"

    paid_date = "N/A"
    if payment.paid_at:
        paid_date = payment.paid_at.strftime("%d/%m/%Y %H:%M")

    remaining_text = ""
    if invoice:
        remaining = invoice.total_amount - invoice.amount_paid
        if remaining > 0:
            remaining_text = (
                f"\nRemaining Balance: N{remaining:,.0f}\n"
                "Reply 'menu' and select 'Make Payment' to pay the rest."
            )
        else:
            remaining_text = "\nAll fees are now settled. Thank you!"

    receipt_text = (
        f"Payment Received!\n\n"
        f"Reference: {payment.reference}\n"
        f"Invoice: {invoice_number}\n"
        f"Description: {invoice_title}\n"
        f"Amount Paid: N{payment.amount:,.0f} {payment.currency}\n"
        f"Date: {paid_date}\n"
        f"Status: Confirmed"
        f"{remaining_text}"
    )

    try:
        await wa_service.send_text(payment.whatsapp_number, receipt_text)
    except Exception:
        logger.exception(
            "Failed to send invoice receipt for payment %s", payment.reference
        )
