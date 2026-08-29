import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.services import notification_service, registration_service
from app.utils.auth import get_current_user

router = APIRouter(tags=["engagement"])


class AttendanceRequest(BaseModel):
    student_id: uuid.UUID
    date: str
    status: str  # present, absent, late
    programme_name: str | None = None


class ProgressNotifyRequest(BaseModel):
    student_id: uuid.UUID
    notification_type: str  # assignment_due, grade_posted, milestone
    title: str
    message: str
    due_date: str | None = None


class CertificateNotifyRequest(BaseModel):
    student_id: uuid.UUID
    programme_name: str
    certificate_url: str | None = None


@router.post("/attendance")
async def attendance_notification(
    req: AttendanceRequest,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    student = await _get_student_with_parent(req.student_id, db)
    parent = student["parent"]

    status_label = {
        "present": "present",
        "absent": "absent",
        "late": "arrived late",
    }.get(req.status, req.status)

    body = (
        f"Attendance update for *{student['name']}*\n\n"
        f"Date: {req.date}\n"
        f"Status: {status_label.title()}\n"
    )
    if req.programme_name:
        body += f"Programme: {req.programme_name}\n"

    if req.status == "absent":
        body += (
            "\nIf this is unexpected, please contact us by "
            "replying 'menu' and selecting Get Help."
        )

    await notification_service.send_notification(
        recipient_whatsapp=parent.whatsapp_number,
        notification_type="attendance",
        message_body=body,
        db=db,
        parent_id=parent.id,
        student_id=req.student_id,
        event_key=f"attendance_{req.student_id}_{req.date}",
    )
    return {"status": "sent", "student_id": str(req.student_id)}


@router.post("/progress/notify")
async def progress_notification(
    req: ProgressNotifyRequest,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    student = await _get_student_with_parent(req.student_id, db)
    parent = student["parent"]

    body = f"*{req.title}*\n\n{req.message}\n\nStudent: {student['name']}"
    if req.due_date:
        body += f"\nDue: {req.due_date}"

    await notification_service.send_notification(
        recipient_whatsapp=parent.whatsapp_number,
        notification_type="progress_report",
        message_body=body,
        db=db,
        parent_id=parent.id,
        student_id=req.student_id,
        event_key=f"progress_{req.notification_type}_{req.student_id}_{req.title[:30]}",
    )
    return {"status": "sent", "student_id": str(req.student_id)}


@router.post("/certificate/notify")
async def certificate_notification(
    req: CertificateNotifyRequest,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    student = await _get_student_with_parent(req.student_id, db)
    parent = student["parent"]

    body = (
        f"Congratulations! *{student['name']}* has completed "
        f"the *{req.programme_name}* programme!\n\n"
        f"A certificate of completion is now available."
    )
    if req.certificate_url:
        body += f"\n\nDownload: {req.certificate_url}"

    await notification_service.send_notification(
        recipient_whatsapp=parent.whatsapp_number,
        notification_type="certificate",
        message_body=body,
        db=db,
        parent_id=parent.id,
        student_id=req.student_id,
        event_key=f"certificate_{req.student_id}_{req.programme_name[:30]}",
    )
    return {"status": "sent", "student_id": str(req.student_id)}


async def _get_student_with_parent(
    student_id: uuid.UUID, db: AsyncSession
) -> dict:
    from sqlalchemy import select
    from app.models.student import Student
    from app.models.parent import Parent

    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    result = await db.execute(
        select(Parent).where(Parent.id == student.parent_id)
    )
    parent = result.scalar_one_or_none()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    return {"name": student.full_name, "parent": parent}
