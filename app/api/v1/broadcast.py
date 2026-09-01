import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.services import broadcast_service
from app.utils.auth import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])


class BroadcastCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4096)
    segment_type: str = "all"
    segment_value: str | None = Field(default=None, max_length=200)


class BroadcastOut(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    segment_type: str
    segment_value: str | None
    status: str
    recipient_count: int
    delivered_count: int
    sent_at: str | None = None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, b) -> "BroadcastOut":
        return cls(
            id=b.id,
            title=b.title,
            body=b.body,
            segment_type=b.segment_type,
            segment_value=b.segment_value,
            status=b.status,
            recipient_count=b.recipient_count,
            delivered_count=b.delivered_count,
            sent_at=b.sent_at.isoformat() if b.sent_at else None,
            created_at=b.created_at.isoformat(),
        )


@router.post("", response_model=BroadcastOut, status_code=201)
async def create_broadcast(
    data: BroadcastCreate,
    user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> BroadcastOut:
    broadcast = await broadcast_service.create_broadcast(
        title=data.title,
        body=data.body,
        segment_type=data.segment_type,
        segment_value=data.segment_value,
        db=db,
    )
    await db.commit()
    await db.refresh(broadcast)
    return BroadcastOut.from_model(broadcast)


@router.get("", response_model=list[BroadcastOut])
async def list_broadcasts(
    limit: int = 50,
    offset: int = 0,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BroadcastOut]:
    broadcasts = await broadcast_service.list_broadcasts(db, limit=limit, offset=offset)
    return [BroadcastOut.from_model(b) for b in broadcasts]


@router.get("/{broadcast_id}", response_model=BroadcastOut)
async def get_broadcast(
    broadcast_id: uuid.UUID,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BroadcastOut:
    broadcast = await broadcast_service.get_broadcast(broadcast_id, db)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return BroadcastOut.from_model(broadcast)


@router.post("/{broadcast_id}/preview")
async def preview_broadcast(
    broadcast_id: uuid.UUID,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    broadcast = await broadcast_service.get_broadcast(broadcast_id, db)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    count = await broadcast_service.preview_broadcast(broadcast_id, db)
    return {"recipient_count": count}


@router.post("/{broadcast_id}/send")
async def send_broadcast(
    broadcast_id: uuid.UUID,
    user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    broadcast = await broadcast_service.get_broadcast(broadcast_id, db)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    if broadcast.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send a broadcast with status '{broadcast.status}'. Only draft broadcasts can be sent.",
        )
    recipient_count = await broadcast_service.preview_broadcast(broadcast_id, db)
    if recipient_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No recipients match the selected segment.",
        )
    await broadcast_service.mark_sending(broadcast_id, user.id, recipient_count, db)
    await db.commit()

    from app.tasks.broadcast_tasks import fan_out_broadcast
    task = fan_out_broadcast.delay(str(broadcast_id))

    return {"status": "queued", "task_id": task.id, "recipient_count": recipient_count}


@router.delete("/{broadcast_id}")
async def cancel_broadcast(
    broadcast_id: uuid.UUID,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    broadcast = await broadcast_service.cancel_broadcast(broadcast_id, db)
    if not broadcast:
        raise HTTPException(
            status_code=400,
            detail="Broadcast not found or cannot be cancelled (only draft broadcasts can be cancelled).",
        )
    await db.commit()
    return {"status": "cancelled", "id": str(broadcast_id)}
