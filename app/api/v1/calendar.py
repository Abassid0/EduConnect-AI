import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.calendar import AcademicEventCreate, AcademicEventOut, AcademicEventUpdate
from app.services import calendar_service
from app.utils.auth import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/events", response_model=list[AcademicEventOut])
async def list_events(
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AcademicEventOut]:
    events = await calendar_service.list_all_events(db)
    return [AcademicEventOut.model_validate(e) for e in events]


@router.get("/events/upcoming", response_model=list[AcademicEventOut])
async def upcoming_events(
    days: int = 30,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AcademicEventOut]:
    events = await calendar_service.get_upcoming_events(db, days=days)
    return [AcademicEventOut.model_validate(e) for e in events]


@router.post("/events", response_model=AcademicEventOut, status_code=201)
async def create_event(
    data: AcademicEventCreate,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> AcademicEventOut:
    event = await calendar_service.create_event(
        title=data.title,
        event_type=data.event_type,
        start_date=data.start_date,
        db=db,
        end_date=data.end_date,
        description=data.description,
        school_term=data.school_term,
        is_published=data.is_published,
    )
    return AcademicEventOut.model_validate(event)


@router.put("/events/{event_id}", response_model=AcademicEventOut)
async def update_event(
    event_id: uuid.UUID,
    data: AcademicEventUpdate,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> AcademicEventOut:
    fields = data.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    event = await calendar_service.update_event(event_id, db, **fields)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return AcademicEventOut.model_validate(event)


@router.delete("/events/{event_id}", status_code=204)
async def deactivate_event(
    event_id: uuid.UUID,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    ok = await calendar_service.deactivate_event(event_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")
