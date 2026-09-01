import logging
import uuid
from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment_plan import PaymentPlan, PaymentPlanInstallment

logger = logging.getLogger(__name__)


def _add_frequency(d: date, frequency: str) -> date:
    if frequency == "weekly":
        from datetime import timedelta
        return d + timedelta(days=7)
    if frequency == "biweekly":
        from datetime import timedelta
        return d + timedelta(days=14)
    # monthly
    month = d.month + 1
    year = d.year
    if month > 12:
        month = 1
        year += 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


async def create_plan(
    invoice_id: uuid.UUID,
    parent_id: uuid.UUID,
    installment_count: int,
    frequency: str,
    start_date: date,
    db: AsyncSession,
    student_id: uuid.UUID | None = None,
    created_by: uuid.UUID | None = None,
) -> PaymentPlan:
    from app.models.invoice import Invoice

    if installment_count < 2 or installment_count > 24:
        raise ValueError("Installment count must be between 2 and 24.")
    if frequency not in ("weekly", "biweekly", "monthly"):
        raise ValueError("Frequency must be weekly, biweekly, or monthly.")

    invoice_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = invoice_result.scalar_one_or_none()
    if not invoice:
        raise ValueError("Invoice not found.")
    if invoice.status not in ("unpaid", "sent", "overdue", "partial"):
        raise ValueError(f"Cannot create a plan for an invoice with status '{invoice.status}'.")

    existing = await get_plan_for_invoice(invoice_id, db)
    if existing:
        raise ValueError("This invoice already has a payment plan.")

    total = invoice.total_amount
    unit = (total / installment_count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    remainder = total - unit * (installment_count - 1)

    plan = PaymentPlan(
        id=uuid.uuid4(),
        invoice_id=invoice_id,
        parent_id=parent_id,
        student_id=student_id or invoice.student_id,
        total_amount=total,
        installment_count=installment_count,
        frequency=frequency,
        start_date=start_date,
        status="active",
        created_by=created_by,
    )
    db.add(plan)
    await db.flush()

    due = start_date
    for i in range(1, installment_count + 1):
        amount = remainder if i == installment_count else unit
        inst = PaymentPlanInstallment(
            id=uuid.uuid4(),
            plan_id=plan.id,
            installment_number=i,
            due_date=due,
            amount=amount,
            status="pending",
        )
        db.add(inst)
        if i < installment_count:
            due = _add_frequency(due, frequency)

    invoice.status = "on_plan"
    await db.flush()
    await db.refresh(plan)
    return plan


async def get_plan(plan_id: uuid.UUID, db: AsyncSession) -> PaymentPlan | None:
    result = await db.execute(select(PaymentPlan).where(PaymentPlan.id == plan_id))
    return result.scalar_one_or_none()


async def list_plans(
    db: AsyncSession,
    parent_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[PaymentPlan]:
    query = select(PaymentPlan).order_by(PaymentPlan.created_at.desc()).limit(limit).offset(offset)
    if parent_id:
        query = query.where(PaymentPlan.parent_id == parent_id)
    if status:
        query = query.where(PaymentPlan.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_plan_for_invoice(invoice_id: uuid.UUID, db: AsyncSession) -> PaymentPlan | None:
    result = await db.execute(
        select(PaymentPlan).where(PaymentPlan.invoice_id == invoice_id)
    )
    return result.scalar_one_or_none()


async def get_active_plan_for_parent(parent_id: uuid.UUID, db: AsyncSession) -> PaymentPlan | None:
    result = await db.execute(
        select(PaymentPlan)
        .where(PaymentPlan.parent_id == parent_id, PaymentPlan.status == "active")
        .order_by(PaymentPlan.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _check_completion(plan: PaymentPlan, db: AsyncSession) -> None:
    """Auto-complete plan and invoice if all installments are paid/waived."""
    if plan.status in ("completed", "cancelled"):
        return
    all_done = all(i.status in ("paid", "waived") for i in plan.installments)
    if all_done:
        plan.status = "completed"
        if plan.invoice_id:
            from app.models.invoice import Invoice
            inv_result = await db.execute(select(Invoice).where(Invoice.id == plan.invoice_id))
            invoice = inv_result.scalar_one_or_none()
            if invoice:
                invoice.status = "paid"
                invoice.paid_at = datetime.now(timezone.utc)
        await db.flush()


async def get_installment_in_plan(
    plan_id: uuid.UUID,
    installment_id: uuid.UUID,
    db: AsyncSession,
) -> PaymentPlanInstallment | None:
    """Fetch an installment only if it really belongs to the given plan.

    A URL like /plans/{plan_id}/installments/{inst_id} asserts a
    relationship between the two IDs. Nothing enforces that on its own, so
    callers use this to verify the pair before mutating the installment —
    otherwise a mismatched pair would silently update another plan's record.
    """
    result = await db.execute(
        select(PaymentPlanInstallment).where(
            PaymentPlanInstallment.id == installment_id,
            PaymentPlanInstallment.plan_id == plan_id,
        )
    )
    return result.scalar_one_or_none()


async def mark_installment_paid(
    installment_id: uuid.UUID, db: AsyncSession
) -> PaymentPlanInstallment:
    result = await db.execute(
        select(PaymentPlanInstallment).where(PaymentPlanInstallment.id == installment_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise ValueError("Installment not found.")
    inst.status = "paid"
    inst.paid_at = datetime.now(timezone.utc)
    await db.flush()

    plan = await get_plan(inst.plan_id, db)
    if plan:
        await _check_completion(plan, db)
    return inst


async def waive_installment(
    installment_id: uuid.UUID, db: AsyncSession
) -> PaymentPlanInstallment:
    result = await db.execute(
        select(PaymentPlanInstallment).where(PaymentPlanInstallment.id == installment_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise ValueError("Installment not found.")
    inst.status = "waived"
    await db.flush()

    plan = await get_plan(inst.plan_id, db)
    if plan:
        await _check_completion(plan, db)
    return inst


async def cancel_plan(plan_id: uuid.UUID, db: AsyncSession) -> PaymentPlan:
    plan = await get_plan(plan_id, db)
    if not plan:
        raise ValueError("Plan not found.")
    plan.status = "cancelled"

    if plan.invoice_id:
        from app.models.invoice import Invoice
        inv_result = await db.execute(select(Invoice).where(Invoice.id == plan.invoice_id))
        invoice = inv_result.scalar_one_or_none()
        if invoice:
            unpaid = any(i.status not in ("paid", "waived") for i in plan.installments)
            invoice.status = "overdue" if unpaid else "paid"
            if not unpaid:
                invoice.paid_at = datetime.now(timezone.utc)

    await db.flush()
    return plan


async def check_and_mark_overdue(db: AsyncSession) -> int:
    today = date.today()
    result = await db.execute(
        select(PaymentPlanInstallment).where(
            PaymentPlanInstallment.status == "pending",
            PaymentPlanInstallment.due_date < today,
        )
    )
    installments = list(result.scalars().all())
    for inst in installments:
        inst.status = "overdue"
    await db.flush()
    logger.info("Marked %d installments as overdue", len(installments))
    return len(installments)


async def get_parent_plan_summary(parent_id: uuid.UUID, db: AsyncSession) -> dict | None:
    plan = await get_active_plan_for_parent(parent_id, db)
    if not plan:
        return None

    paid_amount = sum(
        i.amount for i in plan.installments if i.status in ("paid", "waived")
    )
    remaining_amount = plan.total_amount - paid_amount
    paid_count = sum(1 for i in plan.installments if i.status in ("paid", "waived"))

    next_inst = next(
        (i for i in plan.installments if i.status in ("pending", "overdue")), None
    )
    overdue_count = sum(1 for i in plan.installments if i.status == "overdue")

    return {
        "plan_id": str(plan.id),
        "total_amount": plan.total_amount,
        "paid_amount": paid_amount,
        "remaining_amount": remaining_amount,
        "installment_count": plan.installment_count,
        "paid_count": paid_count,
        "overdue_count": overdue_count,
        "frequency": plan.frequency,
        "next_installment": {
            "number": next_inst.installment_number,
            "due_date": next_inst.due_date,
            "amount": next_inst.amount,
            "status": next_inst.status,
        } if next_inst else None,
    }
