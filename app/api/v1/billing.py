import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.billing import (
    BillingStatsOut,
    FeeBreakdownOut,
    FeeTypeCreate,
    FeeTypeOut,
    FeeTypeUpdate,
    GenerateTermInvoicesRequest,
    InvoiceBulkCreate,
    InvoiceCreate,
    InvoiceListOut,
    InvoiceOut,
    InvoiceSendRequest,
    ParentBalanceOut,
    ProgrammeFeeItemCreate,
    ProgrammeFeeItemOut,
    ProgrammeFeeItemUpdate,
)
from app.services import billing_service
from app.services.notification_service import send_notification
from app.utils.auth import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Fee Types
# ---------------------------------------------------------------------------


@router.post(
    "/fee-types",
    response_model=FeeTypeOut,
    status_code=201,
)
async def create_fee_type(
    data: FeeTypeCreate,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> FeeTypeOut:
    fee_type = await billing_service.create_fee_type(
        name=data.name,
        slug=data.generate_slug(),
        category=data.category,
        db=db,
        description=data.description,
        default_amount=data.default_amount,
        currency=data.currency,
        is_recurring=data.is_recurring,
    )
    return FeeTypeOut.model_validate(fee_type)


@router.get("/fee-types", response_model=list[FeeTypeOut])
async def list_fee_types(
    include_inactive: bool = False,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FeeTypeOut]:
    fee_types = await billing_service.list_fee_types(
        db, active_only=not include_inactive
    )
    return [FeeTypeOut.model_validate(ft) for ft in fee_types]


@router.put("/fee-types/{fee_type_id}", response_model=FeeTypeOut)
async def update_fee_type(
    fee_type_id: uuid.UUID,
    data: FeeTypeUpdate,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> FeeTypeOut:
    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    fee_type = await billing_service.update_fee_type(fee_type_id, updates, db)
    if not fee_type:
        raise HTTPException(status_code=404, detail="Fee type not found")
    return FeeTypeOut.model_validate(fee_type)


@router.delete("/fee-types/{fee_type_id}", response_model=FeeTypeOut)
async def delete_fee_type(
    fee_type_id: uuid.UUID,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> FeeTypeOut:
    fee_type = await billing_service.deactivate_fee_type(fee_type_id, db)
    if not fee_type:
        raise HTTPException(status_code=404, detail="Fee type not found")
    return FeeTypeOut.model_validate(fee_type)


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


@router.post(
    "/invoices",
    response_model=InvoiceOut,
    status_code=201,
)
async def create_invoice(
    data: InvoiceCreate,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> InvoiceOut:
    items = [
        {
            "fee_type_id": item.fee_type_id,
            "description": item.description,
            "quantity": item.quantity,
            "unit_amount": item.unit_amount,
        }
        for item in data.items
    ]
    invoice = await billing_service.create_invoice(
        parent_id=data.parent_id,
        title=data.title,
        items=items,
        db=db,
        student_id=data.student_id,
        academic_term=data.academic_term,
        due_date=data.due_date,
        notes=data.notes,
    )
    return InvoiceOut.model_validate(invoice)


@router.post(
    "/invoices/bulk",
    response_model=list[InvoiceListOut],
    status_code=201,
)
async def bulk_create_invoices(
    data: InvoiceBulkCreate,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceListOut]:
    items = [
        {
            "fee_type_id": item.fee_type_id,
            "description": item.description,
            "quantity": item.quantity,
            "unit_amount": item.unit_amount,
        }
        for item in data.items
    ]
    invoices = await billing_service.bulk_create_invoices(
        student_ids=data.student_ids,
        title=data.title,
        items=items,
        db=db,
        academic_term=data.academic_term,
        due_date=data.due_date,
        notes=data.notes,
    )
    return [InvoiceListOut.model_validate(inv) for inv in invoices]


@router.get("/invoices", response_model=list[InvoiceListOut])
async def list_invoices(
    parent_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    status: str | None = None,
    academic_term: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceListOut]:
    invoices = await billing_service.list_invoices(
        db,
        parent_id=parent_id,
        student_id=student_id,
        status=status,
        academic_term=academic_term,
        limit=limit,
        offset=offset,
    )
    return [InvoiceListOut.model_validate(inv) for inv in invoices]


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: uuid.UUID,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> InvoiceOut:
    invoice = await billing_service.get_invoice(invoice_id, db)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceOut.model_validate(invoice)


@router.post("/invoices/{invoice_id}/cancel", response_model=InvoiceOut)
async def cancel_invoice(
    invoice_id: uuid.UUID,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> InvoiceOut:
    try:
        invoice = await billing_service.cancel_invoice(invoice_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceOut.model_validate(invoice)


@router.post("/invoices/{invoice_id}/send")
async def send_invoice_notification(
    invoice_id: uuid.UUID,
    data: InvoiceSendRequest | None = None,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    invoice = await billing_service.get_invoice(invoice_id, db)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    parent = invoice.parent
    if not parent:
        raise HTTPException(status_code=400, detail="Parent not found for invoice")

    items_text = "\n".join(
        f"  - {item.description}: N{item.total_amount:,.0f}"
        for item in invoice.items
    )
    due_str = invoice.due_date.strftime("%d/%m/%Y") if invoice.due_date else "No due date"

    custom = ""
    if data and data.custom_message:
        custom = f"\n{data.custom_message}\n"

    message = (
        f"New Invoice: {invoice.title}\n\n"
        f"Invoice #: {invoice.invoice_number}\n"
        f"Items:\n{items_text}\n\n"
        f"Total: N{invoice.total_amount:,.0f}\n"
        f"Due: {due_str}\n"
        f"{custom}\n"
        f"Reply 'menu' and select 'Make Payment' to pay now."
    )

    await send_notification(
        recipient_whatsapp=parent.whatsapp_number,
        notification_type="invoice_notification",
        message_body=message,
        db=db,
        parent_id=parent.id,
        student_id=invoice.student_id,
        event_key=f"invoice_sent:{invoice.id}",
    )

    return {"status": "sent", "invoice_number": invoice.invoice_number}


@router.post("/invoices/{invoice_id}/remind")
async def remind_invoice(
    invoice_id: uuid.UUID,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    invoice = await billing_service.get_invoice(invoice_id, db)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status in ("paid", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Invoice is already {invoice.status}",
        )

    parent = invoice.parent
    if not parent:
        raise HTTPException(status_code=400, detail="Parent not found for invoice")

    remaining = invoice.amount_remaining
    due_str = invoice.due_date.strftime("%d/%m/%Y") if invoice.due_date else "N/A"

    message = (
        f"Payment Reminder\n\n"
        f"Invoice: {invoice.title}\n"
        f"Invoice #: {invoice.invoice_number}\n"
        f"Amount Due: N{remaining:,.0f}\n"
        f"Due Date: {due_str}\n\n"
        f"Please reply 'menu' and select 'Make Payment' to pay now."
    )

    await send_notification(
        recipient_whatsapp=parent.whatsapp_number,
        notification_type="invoice_reminder",
        message_body=message,
        db=db,
        parent_id=parent.id,
        student_id=invoice.student_id,
        event_key=f"invoice_remind:{invoice.id}:{datetime.now(timezone.utc).strftime('%Y%m%d')}",
    )

    return {"status": "sent", "invoice_number": invoice.invoice_number}


# ---------------------------------------------------------------------------
# Parent Balance
# ---------------------------------------------------------------------------


@router.get(
    "/parent/{parent_id}/balance",
    response_model=ParentBalanceOut,
)
async def parent_balance(
    parent_id: uuid.UUID,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> ParentBalanceOut:
    balance = await billing_service.get_parent_balance(parent_id, db)
    return ParentBalanceOut(**balance)


@router.get(
    "/parent/{parent_id}/invoices",
    response_model=list[InvoiceListOut],
)
async def parent_invoices(
    parent_id: uuid.UUID,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceListOut]:
    invoices = await billing_service.list_invoices(
        db, parent_id=parent_id, status=status, limit=limit, offset=offset
    )
    return [InvoiceListOut.model_validate(inv) for inv in invoices]


# ---------------------------------------------------------------------------
# Billing Stats
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=BillingStatsOut)
async def billing_stats(
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> BillingStatsOut:
    stats = await billing_service.get_billing_stats(db)
    return BillingStatsOut(**stats)


# ---------------------------------------------------------------------------
# Programme Fee Items (fee breakdown templates)
# ---------------------------------------------------------------------------


@router.post(
    "/programmes/{programme_id}/fee-items",
    response_model=ProgrammeFeeItemOut,
    status_code=201,
)
async def add_programme_fee_item(
    programme_id: uuid.UUID,
    data: ProgrammeFeeItemCreate,
    _user: AdminUser = Depends(require_role("super_admin", "admin", "finance")),
    db: AsyncSession = Depends(get_db),
) -> ProgrammeFeeItemOut:
    item = await billing_service.add_programme_fee_item(
        programme_id=programme_id,
        fee_type_id=data.fee_type_id,
        amount=data.amount,
        db=db,
        term=data.term,
        is_optional=data.is_optional,
    )
    return ProgrammeFeeItemOut.model_validate(item)


@router.get(
    "/programmes/{programme_id}/fee-items",
    response_model=list[ProgrammeFeeItemOut],
)
async def list_programme_fee_items(
    programme_id: uuid.UUID,
    term: str | None = None,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProgrammeFeeItemOut]:
    items = await billing_service.list_programme_fee_items(
        programme_id, db, term=term
    )
    return [ProgrammeFeeItemOut.model_validate(i) for i in items]


@router.get(
    "/programmes/{programme_id}/fee-breakdown",
    response_model=FeeBreakdownOut,
)
async def get_fee_breakdown(
    programme_id: uuid.UUID,
    term: str = "first",
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeeBreakdownOut:
    breakdown = await billing_service.get_fee_breakdown_for_programme(
        programme_id, term, db
    )
    return FeeBreakdownOut(
        mandatory_items=[
            ProgrammeFeeItemOut.model_validate(i)
            for i in breakdown["mandatory_items"]
        ],
        optional_items=[
            ProgrammeFeeItemOut.model_validate(i)
            for i in breakdown["optional_items"]
        ],
        mandatory_total=breakdown["mandatory_total"],
        optional_total=breakdown["optional_total"],
        grand_total=breakdown["grand_total"],
    )


@router.patch(
    "/fee-items/{item_id}",
    response_model=ProgrammeFeeItemOut,
)
async def update_programme_fee_item(
    item_id: uuid.UUID,
    data: ProgrammeFeeItemUpdate,
    _user: AdminUser = Depends(require_role("super_admin", "admin", "finance")),
    db: AsyncSession = Depends(get_db),
) -> ProgrammeFeeItemOut:
    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    item = await billing_service.update_programme_fee_item(item_id, updates, db)
    if not item:
        raise HTTPException(status_code=404, detail="Fee item not found")
    return ProgrammeFeeItemOut.model_validate(item)


@router.delete("/fee-items/{item_id}", response_model=ProgrammeFeeItemOut)
async def delete_programme_fee_item(
    item_id: uuid.UUID,
    _user: AdminUser = Depends(require_role("super_admin", "admin", "finance")),
    db: AsyncSession = Depends(get_db),
) -> ProgrammeFeeItemOut:
    item = await billing_service.remove_programme_fee_item(item_id, db)
    if not item:
        raise HTTPException(status_code=404, detail="Fee item not found")
    return ProgrammeFeeItemOut.model_validate(item)


# ---------------------------------------------------------------------------
# Generate Term Invoices
# ---------------------------------------------------------------------------


@router.post(
    "/generate-term-invoices",
    response_model=list[InvoiceListOut],
    status_code=201,
)
async def generate_term_invoices(
    data: GenerateTermInvoicesRequest,
    _user: AdminUser = Depends(require_role("super_admin", "admin", "finance")),
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceListOut]:
    invoices = await billing_service.generate_term_invoices_for_programme(
        programme_id=data.programme_id,
        term=data.term,
        academic_year=data.academic_year,
        db=db,
        due_date=data.due_date,
        include_optional=data.include_optional,
    )
    return [InvoiceListOut.model_validate(inv) for inv in invoices]


# ---------------------------------------------------------------------------
# Manual Task Triggers
# ---------------------------------------------------------------------------


@router.post("/tasks/send-reminders")
async def trigger_invoice_reminders(
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
) -> dict:
    from app.tasks.invoice_tasks import send_invoice_reminders
    task = send_invoice_reminders.delay()
    return {"status": "queued", "task_id": task.id}


@router.post("/tasks/check-overdue")
async def trigger_overdue_check(
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
) -> dict:
    from app.tasks.invoice_tasks import check_overdue_invoices
    task = check_overdue_invoices.delay()
    return {"status": "queued", "task_id": task.id}


