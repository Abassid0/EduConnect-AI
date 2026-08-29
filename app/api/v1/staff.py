import uuid

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.support_ticket import SupportTicket
from app.schemas.admin import AdminUserCreate, AdminUserOut
from app.utils.auth import require_role

router = APIRouter(prefix="/staff", tags=["staff"])

VALID_ROLES = ["super_admin", "admin", "support_agent", "finance", "academic"]


class StaffUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    department: str | None = None
    is_active: bool | None = None


class StaffDetailOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    department: str | None = None
    is_active: bool = True
    last_login_at: str | None = None
    created_at: str
    open_tickets: int = 0

    class Config:
        from_attributes = True


class PasswordReset(BaseModel):
    new_password: str


@router.get("", response_model=list[StaffDetailOut])
async def list_staff(
    role: str | None = None,
    active_only: bool = True,
    current_user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> list[StaffDetailOut]:
    query = select(AdminUser).order_by(AdminUser.full_name)
    if role:
        query = query.where(AdminUser.role == role)
    if active_only:
        query = query.where(AdminUser.is_active == True)

    result = await db.execute(query)
    users = list(result.scalars().all())

    ticket_counts: dict[uuid.UUID, int] = {}
    if users:
        user_ids = [u.id for u in users]
        count_result = await db.execute(
            select(SupportTicket.assigned_to, func.count(SupportTicket.id))
            .where(
                SupportTicket.assigned_to.in_(user_ids),
                SupportTicket.status.in_(["open", "in_progress"]),
            )
            .group_by(SupportTicket.assigned_to)
        )
        ticket_counts = dict(count_result.all())

    return [
        StaffDetailOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            department=u.department,
            is_active=u.is_active,
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
            created_at=u.created_at.isoformat(),
            open_tickets=ticket_counts.get(u.id, 0),
        )
        for u in users
    ]


@router.post("", response_model=AdminUserOut, status_code=201)
async def create_staff(
    data: AdminUserCreate,
    current_user: AdminUser = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminUserOut:
    existing = await db.execute(
        select(AdminUser).where(AdminUser.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    if data.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}",
        )

    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    user = AdminUser(
        id=uuid.uuid4(),
        email=data.email,
        full_name=data.full_name,
        hashed_password=hashed,
        role=data.role,
        department=data.department,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return AdminUserOut.model_validate(user)


@router.get("/{staff_id}", response_model=StaffDetailOut)
async def get_staff(
    staff_id: uuid.UUID,
    current_user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> StaffDetailOut:
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == staff_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Staff member not found")

    count_result = await db.execute(
        select(func.count(SupportTicket.id)).where(
            SupportTicket.assigned_to == staff_id,
            SupportTicket.status.in_(["open", "in_progress"]),
        )
    )
    open_tickets = count_result.scalar() or 0

    return StaffDetailOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department=user.department,
        is_active=user.is_active,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
        open_tickets=open_tickets,
    )


@router.put("/{staff_id}", response_model=AdminUserOut)
async def update_staff(
    staff_id: uuid.UUID,
    data: StaffUpdate,
    current_user: AdminUser = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminUserOut:
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == staff_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Staff member not found")

    if data.role is not None:
        if data.role not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}",
            )
        user.role = data.role

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.department is not None:
        user.department = data.department
    if data.is_active is not None:
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate yourself",
            )
        user.is_active = data.is_active

    await db.flush()
    await db.refresh(user)
    return AdminUserOut.model_validate(user)


@router.post("/{staff_id}/reset-password")
async def reset_staff_password(
    staff_id: uuid.UUID,
    data: PasswordReset,
    current_user: AdminUser = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == staff_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Staff member not found")

    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    user.hashed_password = bcrypt.hashpw(
        data.new_password.encode(), bcrypt.gensalt()
    ).decode()
    await db.flush()
    return {"status": "password_reset", "staff_id": str(staff_id)}
