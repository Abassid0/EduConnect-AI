import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.registration import EnrollmentOut, ParentOut, StudentOut
from app.services import registration_service
from app.utils.auth import get_current_user

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/parent/{whatsapp_number}", response_model=ParentOut)
async def get_parent(
    whatsapp_number: str,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ParentOut:
    parent = await registration_service.get_parent_by_whatsapp(whatsapp_number, db)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    return ParentOut.model_validate(parent)


@router.get("/parent/{whatsapp_number}/students", response_model=list[StudentOut])
async def list_students(
    whatsapp_number: str,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StudentOut]:
    parent = await registration_service.get_parent_by_whatsapp(whatsapp_number, db)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    students = await registration_service.get_students_for_parent(parent.id, db)
    return [StudentOut.model_validate(s) for s in students]


@router.get("/{student_id}/enrollments", response_model=list[EnrollmentOut])
async def list_enrollments(
    student_id: uuid.UUID,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EnrollmentOut]:
    enrollments = await registration_service.get_enrollments_for_student(
        student_id, db
    )
    return [EnrollmentOut.model_validate(e) for e in enrollments]
