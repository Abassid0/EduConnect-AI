import uuid
from datetime import date, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_event import AcademicEvent


async def list_all_events(db: AsyncSession) -> list[AcademicEvent]:
    result = await db.execute(
        select(AcademicEvent).order_by(AcademicEvent.start_date)
    )
    return list(result.scalars().all())


async def get_upcoming_events(db: AsyncSession, days: int = 30) -> list[AcademicEvent]:
    today = date.today()
    cutoff = today + timedelta(days=days)
    result = await db.execute(
        select(AcademicEvent)
        .where(
            and_(
                AcademicEvent.is_published == True,
                AcademicEvent.start_date >= today,
                AcademicEvent.start_date <= cutoff,
            )
        )
        .order_by(AcademicEvent.start_date)
    )
    return list(result.scalars().all())


async def get_next_7_days_events(db: AsyncSession) -> list[AcademicEvent]:
    return await get_upcoming_events(db, days=7)


async def get_events_by_term(db: AsyncSession, school_term: str) -> list[AcademicEvent]:
    result = await db.execute(
        select(AcademicEvent)
        .where(
            and_(
                AcademicEvent.is_published == True,
                AcademicEvent.school_term == school_term,
            )
        )
        .order_by(AcademicEvent.start_date)
    )
    return list(result.scalars().all())


async def create_event(
    title: str,
    event_type: str,
    start_date: date,
    db: AsyncSession,
    end_date: date | None = None,
    description: str | None = None,
    school_term: str | None = None,
    is_published: bool = True,
) -> AcademicEvent:
    event = AcademicEvent(
        id=uuid.uuid4(),
        title=title,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        description=description,
        school_term=school_term,
        is_published=is_published,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def update_event(
    event_id: uuid.UUID,
    db: AsyncSession,
    **fields,
) -> AcademicEvent | None:
    result = await db.execute(
        select(AcademicEvent).where(AcademicEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        return None
    for key, value in fields.items():
        if value is not None or key in ("description", "end_date", "school_term"):
            setattr(event, key, value)
    await db.commit()
    await db.refresh(event)
    return event


async def deactivate_event(event_id: uuid.UUID, db: AsyncSession) -> bool:
    result = await db.execute(
        select(AcademicEvent).where(AcademicEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        return False
    event.is_published = False
    await db.commit()
    return True
