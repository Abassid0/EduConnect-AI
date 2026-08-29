import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broadcast import Broadcast
from app.models.parent import Parent

logger = logging.getLogger(__name__)


async def resolve_recipients(
    segment_type: str,
    segment_value: str | None,
    db: AsyncSession,
) -> list[Parent]:
    if segment_type == "all":
        result = await db.execute(select(Parent))
        return list(result.scalars().all())

    if segment_type == "programme":
        from app.models.enrollment import Enrollment
        from app.models.student import Student
        if not segment_value:
            return []
        programme_id = uuid.UUID(segment_value)
        result = await db.execute(
            select(Parent)
            .join(Student, Student.parent_id == Parent.id)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .where(
                Enrollment.programme_id == programme_id,
                Enrollment.status.in_(["active", "pending"]),
            )
            .distinct()
        )
        return list(result.scalars().all())

    if segment_type == "has_overdue":
        from app.models.invoice import Invoice
        result = await db.execute(
            select(Parent)
            .join(Invoice, Invoice.parent_id == Parent.id)
            .where(Invoice.status == "overdue")
            .distinct()
        )
        return list(result.scalars().all())

    if segment_type == "specific":
        if not segment_value:
            return []
        try:
            id_list = json.loads(segment_value)
            parent_ids = [uuid.UUID(pid) for pid in id_list]
        except (json.JSONDecodeError, ValueError):
            logger.error("Invalid specific segment_value: %s", segment_value)
            return []
        result = await db.execute(
            select(Parent).where(Parent.id.in_(parent_ids))
        )
        return list(result.scalars().all())

    return []


async def create_broadcast(
    title: str,
    body: str,
    segment_type: str,
    db: AsyncSession,
    segment_value: str | None = None,
) -> Broadcast:
    broadcast = Broadcast(
        id=uuid.uuid4(),
        title=title,
        body=body,
        segment_type=segment_type,
        segment_value=segment_value,
        status="draft",
    )
    db.add(broadcast)
    await db.flush()
    await db.refresh(broadcast)
    return broadcast


async def get_broadcast(broadcast_id: uuid.UUID, db: AsyncSession) -> Broadcast | None:
    result = await db.execute(
        select(Broadcast).where(Broadcast.id == broadcast_id)
    )
    return result.scalar_one_or_none()


async def list_broadcasts(
    db: AsyncSession, limit: int = 50, offset: int = 0
) -> list[Broadcast]:
    result = await db.execute(
        select(Broadcast)
        .order_by(Broadcast.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def preview_broadcast(broadcast_id: uuid.UUID, db: AsyncSession) -> int:
    broadcast = await get_broadcast(broadcast_id, db)
    if not broadcast:
        return 0
    parents = await resolve_recipients(broadcast.segment_type, broadcast.segment_value, db)
    return len(parents)


async def mark_sending(
    broadcast_id: uuid.UUID,
    sent_by_id: uuid.UUID,
    recipient_count: int,
    db: AsyncSession,
) -> Broadcast | None:
    broadcast = await get_broadcast(broadcast_id, db)
    if not broadcast:
        return None
    broadcast.status = "sending"
    broadcast.sent_by = sent_by_id
    broadcast.sent_at = datetime.now(timezone.utc)
    broadcast.recipient_count = recipient_count
    await db.flush()
    return broadcast


async def increment_delivered(broadcast_id: uuid.UUID, db: AsyncSession) -> None:
    await db.execute(
        sa_update(Broadcast)
        .where(Broadcast.id == broadcast_id)
        .values(delivered_count=Broadcast.delivered_count + 1)
    )


async def mark_sent(broadcast_id: uuid.UUID, db: AsyncSession) -> None:
    await db.execute(
        sa_update(Broadcast)
        .where(Broadcast.id == broadcast_id)
        .values(status="sent")
    )


async def cancel_broadcast(
    broadcast_id: uuid.UUID, db: AsyncSession
) -> Broadcast | None:
    broadcast = await get_broadcast(broadcast_id, db)
    if not broadcast or broadcast.status != "draft":
        return None
    broadcast.status = "cancelled"
    await db.flush()
    return broadcast
