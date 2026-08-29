import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.registration import (
    ProgrammeCreate,
    ProgrammeOut,
    ProgrammeUpdate,
    ScheduleCreate,
    ScheduleOut,
)
from app.services import programme_service
from app.utils.auth import require_role

router = APIRouter(prefix="/programmes", tags=["programmes"])


@router.get("/", response_model=list[ProgrammeOut])
async def list_programmes(
    active_only: bool = True,
    age: int | None = None,
    level: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ProgrammeOut]:
    if active_only:
        programmes = await programme_service.get_active_programmes(db, age=age, level=level)
    else:
        programmes = await programme_service.get_all_programmes(db)
    return [ProgrammeOut.model_validate(p) for p in programmes]


@router.post("/", response_model=ProgrammeOut, status_code=201)
async def create_programme(
    data: ProgrammeCreate,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> ProgrammeOut:
    programme = await programme_service.create_programme(
        data.model_dump(), db
    )
    return ProgrammeOut.model_validate(programme)


@router.get("/{programme_id}", response_model=ProgrammeOut)
async def get_programme(
    programme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProgrammeOut:
    programme = await programme_service.get_programme_by_id(programme_id, db)
    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")
    return ProgrammeOut.model_validate(programme)


@router.patch("/{programme_id}", response_model=ProgrammeOut)
async def update_programme(
    programme_id: uuid.UUID,
    data: ProgrammeUpdate,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> ProgrammeOut:
    programme = await programme_service.update_programme(
        programme_id, data.model_dump(exclude_unset=True), db
    )
    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")
    return ProgrammeOut.model_validate(programme)


@router.get("/{programme_id}/schedules", response_model=list[ScheduleOut])
async def list_schedules(
    programme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ScheduleOut]:
    programme = await programme_service.get_programme_by_id(programme_id, db)
    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")
    schedules = await programme_service.get_schedules_for_programme(programme_id, db)
    return [ScheduleOut.model_validate(s) for s in schedules]


@router.post(
    "/{programme_id}/schedules", response_model=ScheduleOut, status_code=201
)
async def create_schedule(
    programme_id: uuid.UUID,
    data: ScheduleCreate,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> ScheduleOut:
    programme = await programme_service.get_programme_by_id(programme_id, db)
    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")
    schedule = await programme_service.create_schedule(
        programme_id=programme_id,
        day_of_week=data.day_of_week,
        start_time=data.start_time,
        end_time=data.end_time,
        timezone=data.timezone,
        db=db,
    )
    return ScheduleOut.model_validate(schedule)


@router.get("/levels/", response_model=list[str])
async def list_levels(
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    return await programme_service.get_levels(db)
