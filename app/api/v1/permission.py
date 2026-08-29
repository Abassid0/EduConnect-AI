import logging
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.services import permission_service
from app.utils.auth import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/permissions", tags=["permissions"])


class SlipCreate(BaseModel):
    title: str
    description: str | None = None
    event_date: date | None = None
    deadline: datetime | None = None
    segment_type: str = "all"
    segment_value: str | None = None


class SlipOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    event_date: date | None
    deadline: str | None
    segment_type: str
    segment_value: str | None
    status: str
    created_at: str
    yes_count: int = 0
    no_count: int = 0
    pending_count: int = 0

    model_config = {"from_attributes": True}


class ResponseOverride(BaseModel):
    response: str


def _slip_out(slip, summary: dict | None = None) -> SlipOut:
    return SlipOut(
        id=slip.id,
        title=slip.title,
        description=slip.description,
        event_date=slip.event_date,
        deadline=slip.deadline.isoformat() if slip.deadline else None,
        segment_type=slip.segment_type,
        segment_value=slip.segment_value,
        status=slip.status,
        created_at=slip.created_at.isoformat(),
        yes_count=summary["yes"] if summary else 0,
        no_count=summary["no"] if summary else 0,
        pending_count=summary["pending"] if summary else 0,
    )


@router.post("/slips", status_code=201, response_model=SlipOut)
async def create_slip(
    data: SlipCreate,
    user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> SlipOut:
    slip = await permission_service.create_slip(
        title=data.title,
        description=data.description,
        event_date=data.event_date,
        deadline=data.deadline,
        segment_type=data.segment_type,
        segment_value=data.segment_value,
        created_by=user.id,
        db=db,
    )
    await db.commit()
    await db.refresh(slip)
    return _slip_out(slip)


@router.get("/slips", response_model=list[SlipOut])
async def list_slips(
    limit: int = 50,
    offset: int = 0,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SlipOut]:
    slips = await permission_service.list_slips(db, limit=limit, offset=offset)
    results = []
    for slip in slips:
        summary = await permission_service.get_slip_response_summary(slip.id, db)
        results.append(_slip_out(slip, summary))
    return results


@router.get("/slips/{slip_id}", response_model=SlipOut)
async def get_slip(
    slip_id: uuid.UUID,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SlipOut:
    slip = await permission_service.get_slip(slip_id, db)
    if not slip:
        raise HTTPException(status_code=404, detail="Permission slip not found")
    summary = await permission_service.get_slip_response_summary(slip_id, db)
    return _slip_out(slip, summary)


@router.post("/slips/{slip_id}/send")
async def send_slip(
    slip_id: uuid.UUID,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    slip = await permission_service.get_slip(slip_id, db)
    if not slip:
        raise HTTPException(status_code=404, detail="Permission slip not found")
    if slip.status != "draft":
        raise HTTPException(
            status_code=400, detail=f"Cannot send a slip with status '{slip.status}'."
        )

    await permission_service.activate_slip(slip_id, db)
    await db.commit()

    from app.tasks.broadcast_tasks import fan_out_permission_slip
    task = fan_out_permission_slip.delay(str(slip_id))

    return {"status": "queued", "task_id": task.id}


@router.get("/slips/{slip_id}/responses")
async def get_responses(
    slip_id: uuid.UUID,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    slip = await permission_service.get_slip(slip_id, db)
    if not slip:
        raise HTTPException(status_code=404, detail="Permission slip not found")
    summary = await permission_service.get_slip_response_summary(slip_id, db)

    response_rows = []
    for r in summary["responses"]:
        response_rows.append({
            "parent_id": str(r.parent_id),
            "student_id": str(r.student_id) if r.student_id else None,
            "response": r.response,
            "responded_at": r.responded_at.isoformat() if r.responded_at else None,
            "responded_via": r.responded_via,
        })

    return {
        "slip_id": str(slip_id),
        "yes": summary["yes"],
        "no": summary["no"],
        "pending": summary["pending"],
        "total_responses": summary["total_responses"],
        "responses": response_rows,
    }


@router.put("/slips/{slip_id}/close")
async def close_slip(
    slip_id: uuid.UUID,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    slip = await permission_service.close_slip(slip_id, db)
    if not slip:
        raise HTTPException(status_code=404, detail="Permission slip not found")
    await db.commit()
    return {"status": "closed", "id": str(slip_id)}


@router.put("/slips/{slip_id}/responses/{parent_id}")
async def override_response(
    slip_id: uuid.UUID,
    parent_id: uuid.UUID,
    data: ResponseOverride,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Admin override — record a paper/verbal response on behalf of a parent."""
    if data.response not in ("yes", "no"):
        raise HTTPException(status_code=400, detail="response must be 'yes' or 'no'")
    try:
        resp = await permission_service.record_response(
            slip_id=slip_id,
            parent_id=parent_id,
            response=data.response,
            db=db,
            responded_via="admin",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return {"status": "recorded", "response": resp.response, "responded_via": resp.responded_via}
