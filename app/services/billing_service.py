import logging
import random
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func as sa_func
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fee_type import FeeType
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.parent import Parent
from app.models.payment import Payment
from app.models.student import Student
from app.services import payment_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fee Types
# ---------------------------------------------------------------------------


async def create_fee_type(
    name: str,
    slug: str,
    category: str,
    db: AsyncSession,
    description: str | None = None,
    default_amount: Decimal | None = None,
    currency: str = "NGN",
    is_recurring: bool = False,
) -> FeeType:
    existing = await db.execute(
        select(FeeType).where(FeeType.slug == slug)
    )
    if existing.scalar_one_or_none():
        suffix = random.randint(100, 999)
        slug = f"{slug}_{suffix}"

    fee_type = FeeType(
        id=uuid.uuid4(),
        name=name,
        slug=slug,
        description=description,
        category=category,
        default_amount=default_amount,
        currency=currency,
        is_recurring=is_recurring,
    )
    db.add(fee_type)
    await db.flush()
    return fee_type


async def list_fee_types(
    db: AsyncSession, active_only: bool = True
) -> list[FeeType]:
    query = select(FeeType).order_by(FeeType.name)
    if active_only:
        query = query.where(FeeType.is_active == True)  # noqa: E712
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_fee_type(
    fee_type_id: uuid.UUID, db: AsyncSession
) -> FeeType | None:
    result = await db.execute(
        select(FeeType).where(FeeType.id == fee_type_id)
    )
    return result.scalar_one_or_none()


async def update_fee_type(
    fee_type_id: uuid.UUID,
    updates: dict,
    db: AsyncSession,
) -> FeeType | None:
    fee_type = await get_fee_type(fee_type_id, db)
    if not fee_type:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(fee_type, key):
            setattr(fee_type, key, value)
    await db.flush()
    await db.refresh(fee_type)
    return fee_type


async def deactivate_fee_type(
    fee_type_id: uuid.UUID, db: AsyncSession
) -> FeeType | None:
    return await update_fee_type(fee_type_id, {"is_active": False}, db)


# ---------------------------------------------------------------------------
# Invoice Number Generation
# ---------------------------------------------------------------------------


def generate_invoice_number() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = random.randint(10000, 99999)
    return f"INV-{ts}-{suffix}"


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


async def create_invoice(
    parent_id: uuid.UUID,
    title: str,
    items: list[dict],
    db: AsyncSession,
    student_id: uuid.UUID | None = None,
    academic_term: str | None = None,
    due_date: date | None = None,
    notes: str | None = None,
) -> Invoice:
    invoice_number = generate_invoice_number()
    existing = await db.execute(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    )
    while existing.scalar_one_or_none() is not None:
        invoice_number = generate_invoice_number()
        existing = await db.execute(
            select(Invoice).where(Invoice.invoice_number == invoice_number)
        )

    total = Decimal("0")
    invoice_items = []
    for item in items:
        qty = item.get("quantity", 1)
        unit = Decimal(str(item["unit_amount"]))
        line_total = qty * unit
        total += line_total
        invoice_items.append(
            InvoiceItem(
                id=uuid.uuid4(),
                fee_type_id=item["fee_type_id"],
                description=item["description"],
                quantity=qty,
                unit_amount=unit,
                total_amount=line_total,
            )
        )

    invoice = Invoice(
        id=uuid.uuid4(),
        invoice_number=invoice_number,
        parent_id=parent_id,
        student_id=student_id,
        academic_term=academic_term,
        title=title,
        total_amount=total,
        amount_paid=Decimal("0"),
        status="unpaid",
        due_date=due_date,
        notes=notes,
    )
    db.add(invoice)
    await db.flush()

    for inv_item in invoice_items:
        inv_item.invoice_id = invoice.id
        db.add(inv_item)
    await db.flush()

    await db.refresh(invoice)
    return invoice


async def bulk_create_invoices(
    student_ids: list[uuid.UUID],
    title: str,
    items: list[dict],
    db: AsyncSession,
    academic_term: str | None = None,
    due_date: date | None = None,
    notes: str | None = None,
) -> list[Invoice]:
    invoices = []
    for student_id in student_ids:
        student_result = await db.execute(
            select(Student).where(Student.id == student_id)
        )
        student = student_result.scalar_one_or_none()
        if not student:
            logger.warning("Student %s not found, skipping", student_id)
            continue

        student_title = f"{title} - {student.full_name}"
        invoice = await create_invoice(
            parent_id=student.parent_id,
            title=student_title,
            items=items,
            db=db,
            student_id=student_id,
            academic_term=academic_term,
            due_date=due_date,
            notes=notes,
        )
        invoices.append(invoice)

    return invoices


async def list_invoices(
    db: AsyncSession,
    parent_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    status: str | None = None,
    academic_term: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Invoice]:
    query = select(Invoice).order_by(Invoice.created_at.desc())
    if parent_id:
        query = query.where(Invoice.parent_id == parent_id)
    if student_id:
        query = query.where(Invoice.student_id == student_id)
    if status:
        query = query.where(Invoice.status == status)
    if academic_term:
        query = query.where(Invoice.academic_term == academic_term)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_invoice(
    invoice_id: uuid.UUID, db: AsyncSession
) -> Invoice | None:
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id)
    )
    return result.scalar_one_or_none()


async def get_invoice_by_number(
    invoice_number: str, db: AsyncSession
) -> Invoice | None:
    result = await db.execute(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    )
    return result.scalar_one_or_none()


async def cancel_invoice(
    invoice_id: uuid.UUID, db: AsyncSession
) -> Invoice | None:
    invoice = await get_invoice(invoice_id, db)
    if not invoice:
        return None
    if invoice.status == "paid":
        raise ValueError("Cannot cancel a paid invoice")
    invoice.status = "cancelled"
    await db.flush()
    return invoice


async def get_outstanding_invoices(
    parent_id: uuid.UUID, db: AsyncSession
) -> list[Invoice]:
    result = await db.execute(
        select(Invoice)
        .where(
            Invoice.parent_id == parent_id,
            Invoice.status.in_(["unpaid", "partial", "overdue"]),
        )
        .order_by(Invoice.due_date.asc().nullslast(), Invoice.created_at.desc())
    )
    return list(result.scalars().all())


async def get_parent_balance(
    parent_id: uuid.UUID, db: AsyncSession
) -> dict:
    invoices = await db.execute(
        select(Invoice).where(
            Invoice.parent_id == parent_id,
            Invoice.status != "cancelled",
        )
    )
    all_invoices = list(invoices.scalars().all())

    total_invoiced = sum(inv.total_amount for inv in all_invoices)
    total_paid = sum(inv.amount_paid for inv in all_invoices)
    outstanding = total_invoiced - total_paid
    overdue_count = sum(1 for inv in all_invoices if inv.status == "overdue")

    return {
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "outstanding": outstanding,
        "invoice_count": len(all_invoices),
        "overdue_count": overdue_count,
    }


# ---------------------------------------------------------------------------
# Invoice Payments
# ---------------------------------------------------------------------------


async def create_invoice_payment(
    invoice_id: uuid.UUID,
    amount: Decimal,
    whatsapp_number: str,
    db: AsyncSession,
    email: str | None = None,
) -> Payment:
    invoice = await get_invoice(invoice_id, db)
    if not invoice:
        raise ValueError("Invoice not found")
    if invoice.status in ("paid", "cancelled"):
        raise ValueError(f"Invoice is already {invoice.status}")

    remaining = invoice.amount_remaining
    if amount > remaining:
        raise ValueError(
            f"Amount N{amount:,.0f} exceeds remaining balance N{remaining:,.0f}"
        )

    reference = payment_service.generate_payment_reference()
    existing = await db.execute(
        select(Payment).where(Payment.reference == reference)
    )
    while existing.scalar_one_or_none() is not None:
        reference = payment_service.generate_payment_reference()
        existing = await db.execute(
            select(Payment).where(Payment.reference == reference)
        )

    payment = Payment(
        id=uuid.uuid4(),
        reference=reference,
        student_id=invoice.student_id or invoice.parent_id,
        invoice_id=invoice.id,
        payment_type="invoice",
        description=invoice.title,
        amount=amount,
        currency=invoice.currency,
        whatsapp_number=whatsapp_number,
        status="pending",
        metadata_={
            "invoice_number": invoice.invoice_number,
            "invoice_title": invoice.title,
        },
    )
    db.add(payment)
    await db.flush()

    payment = await payment_service.initialize_paystack_transaction(
        payment=payment,
        email=email,
        db=db,
    )

    return payment


async def process_invoice_payment(
    payment: Payment, db: AsyncSession
) -> Invoice | None:
    if not payment.invoice_id:
        return None

    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == payment.invoice_id)
        .with_for_update()
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        logger.warning("Invoice %s not found for payment %s", payment.invoice_id, payment.reference)
        return None

    invoice.amount_paid = invoice.amount_paid + payment.amount

    if invoice.amount_paid >= invoice.total_amount:
        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc)
    else:
        invoice.status = "partial"

    await db.flush()
    logger.info(
        "Invoice %s updated: paid=%s, status=%s",
        invoice.invoice_number, invoice.amount_paid, invoice.status,
    )
    return invoice


# ---------------------------------------------------------------------------
# Overdue Check
# ---------------------------------------------------------------------------


async def check_overdue_invoices(db: AsyncSession) -> int:
    today = date.today()
    result = await db.execute(
        update(Invoice)
        .where(
            Invoice.status.in_(["unpaid", "partial"]),
            Invoice.due_date != None,  # noqa: E711
            Invoice.due_date < today,
        )
        .values(status="overdue")
        .returning(Invoice.id)
    )
    overdue_ids = list(result.scalars().all())
    await db.flush()
    return len(overdue_ids)


# ---------------------------------------------------------------------------
# Billing Stats
# ---------------------------------------------------------------------------


async def get_billing_stats(db: AsyncSession) -> dict:
    result = await db.execute(
        select(
            sa_func.count(Invoice.id).label("invoice_count"),
            sa_func.coalesce(sa_func.sum(Invoice.total_amount), 0).label("total_invoiced"),
            sa_func.coalesce(sa_func.sum(Invoice.amount_paid), 0).label("total_collected"),
        ).where(Invoice.status != "cancelled")
    )
    row = result.one()

    outstanding = row.total_invoiced - row.total_collected

    paid_result = await db.execute(
        select(sa_func.count(Invoice.id)).where(Invoice.status == "paid")
    )
    paid_count = paid_result.scalar() or 0

    overdue_result = await db.execute(
        select(
            sa_func.count(Invoice.id).label("count"),
            sa_func.coalesce(
                sa_func.sum(Invoice.total_amount - Invoice.amount_paid), 0
            ).label("amount"),
        ).where(Invoice.status == "overdue")
    )
    overdue_row = overdue_result.one()

    return {
        "total_invoiced": row.total_invoiced,
        "total_collected": row.total_collected,
        "outstanding": outstanding,
        "overdue": overdue_row.amount,
        "invoice_count": row.invoice_count,
        "paid_count": paid_count,
        "overdue_count": overdue_row.count,
    }
