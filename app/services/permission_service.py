import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission_slip import PermissionSlip, PermissionSlipResponse

logger = logging.getLogger(__name__)


async def create_slip(
    title: str,
    segment_type: str,
    db: AsyncSession,
    description: str | None = None,
    event_date=None,
    deadline: datetime | None = None,
    segment_value: str | None = None,
    created_by: uuid.UUID | None = None,
) -> PermissionSlip:
    slip = PermissionSlip(
        id=uuid.uuid4(),
        title=title,
        description=description,
        event_date=event_date,
        deadline=deadline,
        segment_type=segment_type,
        segment_value=segment_value,
        status="draft",
        created_by=created_by,
    )
    db.add(slip)
    await db.flush()
    await db.refresh(slip)
    return slip


async def get_slip(slip_id: uuid.UUID, db: AsyncSession) -> PermissionSlip | None:
    result = await db.execute(select(PermissionSlip).where(PermissionSlip.id == slip_id))
    return result.scalar_one_or_none()


async def list_slips(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[PermissionSlip]:
    result = await db.execute(
        select(PermissionSlip).order_by(PermissionSlip.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def get_pending_slips_for_parent(
    parent_id: uuid.UUID, db: AsyncSession
) -> list[PermissionSlip]:
    """Return active slips the parent has not yet responded to (or has a pending response)."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PermissionSlip)
        .outerjoin(
            PermissionSlipResponse,
            and_(
                PermissionSlipResponse.slip_id == PermissionSlip.id,
                PermissionSlipResponse.parent_id == parent_id,
            ),
        )
        .where(
            PermissionSlip.status == "active",
            (PermissionSlip.deadline == None) | (PermissionSlip.deadline > now),  # noqa: E711
            (PermissionSlipResponse.id == None) | (PermissionSlipResponse.response == "pending"),  # noqa: E711
        )
        .order_by(PermissionSlip.created_at)
    )
    return list(result.scalars().all())


async def record_response(
    slip_id: uuid.UUID,
    parent_id: uuid.UUID,
    response: str,
    db: AsyncSession,
    responded_via: str = "whatsapp",
    student_id: uuid.UUID | None = None,
) -> PermissionSlipResponse:
    """
    Record or update a parent's response. Idempotent — re-submitting the same response
    updates the existing row. Raises ValueError if the slip is closed or past its deadline.
    """
    slip = await get_slip(slip_id, db)
    if not slip:
        raise ValueError("Permission slip not found")
    if slip.status == "closed":
        raise ValueError("This consent request is closed.")
    if slip.deadline and datetime.now(timezone.utc) > slip.deadline:
        raise ValueError("The deadline for this consent request has passed.")

    result = await db.execute(
        select(PermissionSlipResponse).where(
            PermissionSlipResponse.slip_id == slip_id,
            PermissionSlipResponse.parent_id == parent_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.response = response
        existing.responded_at = datetime.now(timezone.utc)
        existing.responded_via = responded_via
        if student_id:
            existing.student_id = student_id
        await db.flush()
        return existing

    resp = PermissionSlipResponse(
        id=uuid.uuid4(),
        slip_id=slip_id,
        parent_id=parent_id,
        student_id=student_id,
        response=response,
        responded_at=datetime.now(timezone.utc),
        responded_via=responded_via,
    )
    db.add(resp)
    await db.flush()
    return resp


async def get_slip_response_summary(slip_id: uuid.UUID, db: AsyncSession) -> dict:
    """Return yes/no/pending counts and the list of per-parent responses."""
    result = await db.execute(
        select(PermissionSlipResponse).where(PermissionSlipResponse.slip_id == slip_id)
    )
    responses = list(result.scalars().all())
    return {
        "yes": sum(1 for r in responses if r.response == "yes"),
        "no": sum(1 for r in responses if r.response == "no"),
        "pending": sum(1 for r in responses if r.response == "pending"),
        "total_responses": len(responses),
        "responses": responses,
    }


async def activate_slip(slip_id: uuid.UUID, db: AsyncSession) -> PermissionSlip | None:
    slip = await get_slip(slip_id, db)
    if not slip:
        return None
    slip.status = "active"
    await db.flush()
    return slip


async def close_slip(slip_id: uuid.UUID, db: AsyncSession) -> PermissionSlip | None:
    slip = await get_slip(slip_id, db)
    if not slip:
        return None
    slip.status = "closed"
    await db.flush()
    return slip
