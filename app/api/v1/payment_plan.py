import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.services import payment_plan_service
from app.utils.auth import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["payment-plans"])


class PlanCreate(BaseModel):
    parent_id: uuid.UUID
    installment_count: int
    frequency: str
    start_date: date
    student_id: uuid.UUID | None = None


class InstallmentOut(BaseModel):
    id: uuid.UUID
    installment_number: int
    due_date: date
    amount: float
    status: str
    paid_at: str | None

    model_config = {"from_attributes": True}


class PlanOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID | None
    parent_id: uuid.UUID
    total_amount: float
    installment_count: int
    frequency: str
    start_date: date
    status: str
    created_at: str
    installments: list[InstallmentOut] = []

    model_config = {"from_attributes": True}


def _plan_out(plan) -> PlanOut:
    return PlanOut(
        id=plan.id,
        invoice_id=plan.invoice_id,
        parent_id=plan.parent_id,
        total_amount=float(plan.total_amount),
        installment_count=plan.installment_count,
        frequency=plan.frequency,
        start_date=plan.start_date,
        status=plan.status,
        created_at=plan.created_at.isoformat(),
        installments=[
            InstallmentOut(
                id=i.id,
                installment_number=i.installment_number,
                due_date=i.due_date,
                amount=float(i.amount),
                status=i.status,
                paid_at=i.paid_at.isoformat() if i.paid_at else None,
            )
            for i in plan.installments
        ],
    )


@router.post("/invoices/{invoice_id}/plan", response_model=PlanOut, status_code=201)
async def create_plan(
    invoice_id: uuid.UUID,
    data: PlanCreate,
    user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> PlanOut:
    try:
        plan = await payment_plan_service.create_plan(
            invoice_id=invoice_id,
            parent_id=data.parent_id,
            installment_count=data.installment_count,
            frequency=data.frequency,
            start_date=data.start_date,
            db=db,
            student_id=data.student_id,
            created_by=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(plan)
    return _plan_out(plan)


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(
    parent_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[PlanOut]:
    plans = await payment_plan_service.list_plans(
        db, parent_id=parent_id, status=status, limit=limit, offset=offset
    )
    return [_plan_out(p) for p in plans]


@router.get("/plans/{plan_id}", response_model=PlanOut)
async def get_plan(
    plan_id: uuid.UUID,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> PlanOut:
    plan = await payment_plan_service.get_plan(plan_id, db)
    if not plan:
        raise HTTPException(status_code=404, detail="Payment plan not found")
    return _plan_out(plan)


@router.get("/parent/{parent_id}/plan", response_model=PlanOut | None)
async def parent_active_plan(
    parent_id: uuid.UUID,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> PlanOut | None:
    plan = await payment_plan_service.get_active_plan_for_parent(parent_id, db)
    return _plan_out(plan) if plan else None


@router.get("/invoices/{invoice_id}/plan", response_model=PlanOut | None)
async def invoice_plan(
    invoice_id: uuid.UUID,
    _user: AdminUser = Depends(
        require_role("super_admin", "admin", "finance")
    ),
    db: AsyncSession = Depends(get_db),
) -> PlanOut | None:
    plan = await payment_plan_service.get_plan_for_invoice(invoice_id, db)
    return _plan_out(plan) if plan else None


@router.post("/plans/{plan_id}/cancel")
async def cancel_plan(
    plan_id: uuid.UUID,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        plan = await payment_plan_service.cancel_plan(plan_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return {"status": "cancelled", "id": str(plan.id)}


@router.put("/plans/{plan_id}/installments/{inst_id}/pay")
async def mark_installment_paid(
    plan_id: uuid.UUID,
    inst_id: uuid.UUID,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if await payment_plan_service.get_installment_in_plan(plan_id, inst_id, db) is None:
        raise HTTPException(
            status_code=404, detail="Installment not found in this plan"
        )

    try:
        inst = await payment_plan_service.mark_installment_paid(inst_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return {
        "status": "paid",
        "installment_number": inst.installment_number,
        "paid_at": inst.paid_at.isoformat() if inst.paid_at else None,
    }


@router.put("/plans/{plan_id}/installments/{inst_id}/waive")
async def waive_installment(
    plan_id: uuid.UUID,
    inst_id: uuid.UUID,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if await payment_plan_service.get_installment_in_plan(plan_id, inst_id, db) is None:
        raise HTTPException(
            status_code=404, detail="Installment not found in this plan"
        )

    try:
        inst = await payment_plan_service.waive_installment(inst_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return {"status": "waived", "installment_number": inst.installment_number}


@router.post("/tasks/check-overdue-installments")
async def trigger_overdue_installments(
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
) -> dict:
    from app.tasks.payment_plan_tasks import check_overdue_installments
    task = check_overdue_installments.delay()
    return {"status": "queued", "task_id": task.id}


@router.post("/tasks/send-installment-reminders")
async def trigger_installment_reminders(
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
) -> dict:
    from app.tasks.payment_plan_tasks import send_installment_reminders
    task = send_installment_reminders.delay()
    return {"status": "queued", "task_id": task.id}
