import uuid
from datetime import time

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_schedule import ClassSchedule
from app.models.programme import Programme


async def get_active_programmes(
    db: AsyncSession,
    age: int | None = None,
    level: str | None = None,
) -> list[Programme]:
    stmt = select(Programme).where(Programme.is_active.is_(True))

    if age is not None:
        stmt = stmt.where(
            (Programme.age_range_min.is_(None) | (Programme.age_range_min <= age)),
            (Programme.age_range_max.is_(None) | (Programme.age_range_max >= age)),
        )
    if level:
        stmt = stmt.where(Programme.level == level)

    stmt = stmt.order_by(Programme.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_programme_by_id(
    programme_id: uuid.UUID, db: AsyncSession
) -> Programme | None:
    result = await db.execute(
        select(Programme).where(Programme.id == programme_id)
    )
    return result.scalar_one_or_none()


async def get_all_programmes(db: AsyncSession) -> list[Programme]:
    result = await db.execute(select(Programme).order_by(Programme.name))
    return list(result.scalars().all())


async def create_programme(
    data: dict,
    db: AsyncSession,
) -> Programme:
    programme = Programme(id=uuid.uuid4(), **data)
    db.add(programme)
    await db.flush()
    return programme


async def update_programme(
    programme_id: uuid.UUID,
    data: dict,
    db: AsyncSession,
) -> Programme | None:
    programme = await get_programme_by_id(programme_id, db)
    if not programme:
        return None
    for key, value in data.items():
        if value is not None:
            setattr(programme, key, value)
    await db.flush()
    return programme


async def get_schedules_for_programme(
    programme_id: uuid.UUID, db: AsyncSession
) -> list[ClassSchedule]:
    result = await db.execute(
        select(ClassSchedule)
        .where(ClassSchedule.programme_id == programme_id)
        .order_by(ClassSchedule.day_of_week, ClassSchedule.start_time)
    )
    return list(result.scalars().all())


async def create_schedule(
    programme_id: uuid.UUID,
    day_of_week: int,
    start_time: time,
    end_time: time,
    timezone: str,
    db: AsyncSession,
) -> ClassSchedule:
    schedule = ClassSchedule(
        id=uuid.uuid4(),
        programme_id=programme_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        timezone=timezone,
    )
    db.add(schedule)
    await db.flush()
    return schedule


async def get_levels(db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Programme.level)
        .where(Programme.is_active.is_(True), Programme.level.isnot(None))
        .distinct()
        .order_by(Programme.level)
    )
    return [row[0] for row in result.all()]
