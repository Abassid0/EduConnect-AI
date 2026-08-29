import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.notification import (
    NotificationListOut,
    NotificationOut,
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
)
from app.services import notification_service, registration_service
from app.utils.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "/preferences/{whatsapp_number}",
    response_model=NotificationPreferenceOut,
)
async def get_preferences(
    whatsapp_number: str,
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceOut:
    parent = await registration_service.get_parent_by_whatsapp(
        whatsapp_number, db
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    prefs = await notification_service.get_or_create_preferences(
        parent.id, db
    )
    return NotificationPreferenceOut.model_validate(prefs)


@router.patch(
    "/preferences/{whatsapp_number}",
    response_model=NotificationPreferenceOut,
)
async def update_preferences(
    whatsapp_number: str,
    data: NotificationPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceOut:
    parent = await registration_service.get_parent_by_whatsapp(
        whatsapp_number, db
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    prefs = await notification_service.update_preferences(
        parent.id, data.model_dump(exclude_unset=True), db
    )
    return NotificationPreferenceOut.model_validate(prefs)


@router.get("/", response_model=list[NotificationListOut])
async def list_notifications(
    status: str | None = None,
    notification_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationListOut]:
    notifications = await notification_service.get_all_notifications(
        db,
        status=status,
        notification_type=notification_type,
        limit=limit,
        offset=offset,
    )
    return [NotificationListOut.model_validate(n) for n in notifications]


@router.get("/{notification_id}", response_model=NotificationOut)
async def get_notification(
    notification_id: uuid.UUID,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationOut:
    from sqlalchemy import select
    from app.models.notification import Notification

    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationOut.model_validate(notification)


@router.get(
    "/parent/{whatsapp_number}",
    response_model=list[NotificationListOut],
)
async def list_parent_notifications(
    whatsapp_number: str,
    limit: int = 20,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationListOut]:
    parent = await registration_service.get_parent_by_whatsapp(
        whatsapp_number, db
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    notifications = await notification_service.get_notifications_for_parent(
        parent.id, db, limit=limit
    )
    return [NotificationListOut.model_validate(n) for n in notifications]
