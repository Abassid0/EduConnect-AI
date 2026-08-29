import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment
from app.models.notification import NotificationPreference
from app.models.parent import Parent
from app.models.student import Student
from app.utils.id_generator import generate_registration_id


# CROSS-PLATFORM SYNC: A registration started on WhatsApp (parent identified via
# whatsapp_number, child name entered) can be continued on web/mobile by calling
# these same endpoints:
#   1. GET /api/v1/students?whatsapp={phone} — look up parent + students
#   2. POST /api/v1/payments — initiate payment for an existing enrollment
#   3. GET /api/v1/programmes — browse programmes (same catalogue)
# The parent.whatsapp_number is the shared key. No duplicate APIs exist — WhatsApp,
# mobile, and web all hit the same FastAPI backend.


async def get_or_create_parent(
    whatsapp_number: str,
    full_name: str | None,
    db: AsyncSession,
) -> Parent:
    result = await db.execute(
        select(Parent).where(Parent.whatsapp_number == whatsapp_number)
    )
    parent = result.scalar_one_or_none()

    if parent is None:
        parent = Parent(
            id=uuid.uuid4(),
            whatsapp_number=whatsapp_number,
            full_name=full_name,
        )
        db.add(parent)
        await db.flush()

        prefs = NotificationPreference(
            id=uuid.uuid4(),
            parent_id=parent.id,
        )
        db.add(prefs)
        await db.flush()
    elif full_name and not parent.full_name:
        parent.full_name = full_name
        await db.flush()

    return parent


async def get_parent_by_whatsapp(
    whatsapp_number: str, db: AsyncSession
) -> Parent | None:
    result = await db.execute(
        select(Parent).where(Parent.whatsapp_number == whatsapp_number)
    )
    return result.scalar_one_or_none()


async def get_students_for_parent(
    parent_id: uuid.UUID, db: AsyncSession
) -> list[Student]:
    result = await db.execute(
        select(Student)
        .where(Student.parent_id == parent_id)
        .order_by(Student.created_at)
    )
    return list(result.scalars().all())


async def create_registration(
    flow_data: dict,
    whatsapp_number: str,
    db: AsyncSession,
) -> tuple[Student, Enrollment]:
    parent = await get_or_create_parent(
        whatsapp_number=whatsapp_number,
        full_name=flow_data.get("parent_name"),
        db=db,
    )

    if flow_data.get("parent_email"):
        parent.email = flow_data["parent_email"]
    if flow_data.get("parent_alt_phone"):
        parent.alt_phone = flow_data["parent_alt_phone"]
    if flow_data.get("consent"):
        parent.consent_given = True
        parent.consent_date = datetime.now(timezone.utc)

    reg_id = generate_registration_id()
    existing = await db.execute(
        select(Student).where(Student.registration_id == reg_id)
    )
    while existing.scalar_one_or_none() is not None:
        reg_id = generate_registration_id()
        existing = await db.execute(
            select(Student).where(Student.registration_id == reg_id)
        )

    dob = flow_data.get("date_of_birth")
    age = None
    if dob:
        if isinstance(dob, str):
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
                try:
                    dob = datetime.strptime(dob, fmt).date()
                    break
                except ValueError:
                    continue
        if isinstance(dob, date):
            today = date.today()
            age = today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )

    student = Student(
        id=uuid.uuid4(),
        parent_id=parent.id,
        registration_id=reg_id,
        full_name=flow_data["child_name"],
        date_of_birth=dob if isinstance(dob, date) else None,
        age=age,
        gender=flow_data.get("gender"),
        emergency_contact_name=flow_data.get("emergency_contact_name"),
        emergency_contact_phone=flow_data.get("emergency_contact_phone"),
        status="registered",
    )
    db.add(student)
    await db.flush()

    enrollment = Enrollment(
        id=uuid.uuid4(),
        student_id=student.id,
        programme_id=uuid.UUID(flow_data["programme_id"]),
        schedule_id=uuid.UUID(flow_data["schedule_id"]) if flow_data.get("schedule_id") else None,
        status="pending",
        enrolled_at=datetime.now(timezone.utc),
    )
    db.add(enrollment)
    await db.flush()

    return student, enrollment


async def get_enrollments_for_student(
    student_id: uuid.UUID, db: AsyncSession
) -> list[Enrollment]:
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student_id)
        .order_by(Enrollment.created_at.desc())
    )
    return list(result.scalars().all())
