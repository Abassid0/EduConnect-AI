import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.services import report_card_service
from app.utils.auth import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(tags=["report-cards"])


class ReportCardCreate(BaseModel):
    student_id: uuid.UUID
    academic_term: str
    overall_grade: str | None = None
    overall_score: float | None = None
    position_in_class: int | None = None
    class_size: int | None = None
    teacher_comment: str | None = None


class SubjectIn(BaseModel):
    subject_name: str
    score: float | None = None
    grade: str | None = None
    teacher_comment: str | None = None
    sort_order: int = 0


class SubjectsPayload(BaseModel):
    subjects: list[SubjectIn]


class ReportCardOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    academic_term: str
    status: str
    published_at: str | None
    overall_grade: str | None
    overall_score: float | None
    position_in_class: int | None
    class_size: int | None
    teacher_comment: str | None
    subject_count: int
    acknowledged_count: int
    total_parents: int
    created_at: str

    model_config = {"from_attributes": True}


def _card_out(card) -> ReportCardOut:
    acknowledged = sum(1 for d in card.deliveries if d.acknowledged_at is not None)
    return ReportCardOut(
        id=card.id,
        student_id=card.student_id,
        academic_term=card.academic_term,
        status=card.status,
        published_at=card.published_at.isoformat() if card.published_at else None,
        overall_grade=card.overall_grade,
        overall_score=float(card.overall_score) if card.overall_score is not None else None,
        position_in_class=card.position_in_class,
        class_size=card.class_size,
        teacher_comment=card.teacher_comment,
        subject_count=len(card.subjects),
        acknowledged_count=acknowledged,
        total_parents=len(card.deliveries),
        created_at=card.created_at.isoformat(),
    )


@router.post("/report-cards", response_model=ReportCardOut, status_code=201)
async def create_report_card(
    data: ReportCardCreate,
    user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> ReportCardOut:
    try:
        card = await report_card_service.create_report_card(
            student_id=data.student_id,
            academic_term=data.academic_term,
            db=db,
            overall_grade=data.overall_grade,
            overall_score=data.overall_score,
            position_in_class=data.position_in_class,
            class_size=data.class_size,
            teacher_comment=data.teacher_comment,
            created_by=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(card)
    return _card_out(card)


@router.get("/report-cards", response_model=list[ReportCardOut])
async def list_report_cards(
    student_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReportCardOut]:
    cards = await report_card_service.list_report_cards(
        db, student_id=student_id, status=status, limit=limit, offset=offset
    )
    return [_card_out(c) for c in cards]


@router.get("/report-cards/{report_card_id}")
async def get_report_card(
    report_card_id: uuid.UUID,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    card = await report_card_service.get_report_card(report_card_id, db)
    if not card:
        raise HTTPException(status_code=404, detail="Report card not found")
    summary = await report_card_service.get_delivery_summary(report_card_id, db)
    return {
        **_card_out(card).model_dump(),
        "subjects": [
            {
                "id": str(s.id),
                "subject_name": s.subject_name,
                "score": float(s.score) if s.score is not None else None,
                "grade": s.grade,
                "teacher_comment": s.teacher_comment,
                "sort_order": s.sort_order,
            }
            for s in sorted(card.subjects, key=lambda s: (s.sort_order, s.subject_name))
        ],
        "delivery_summary": summary,
    }


@router.put("/report-cards/{report_card_id}/subjects")
async def replace_subjects(
    report_card_id: uuid.UUID,
    data: SubjectsPayload,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    card = await report_card_service.get_report_card(report_card_id, db)
    if not card:
        raise HTTPException(status_code=404, detail="Report card not found")
    subjects = await report_card_service.replace_subjects(
        report_card_id,
        [s.model_dump() for s in data.subjects],
        db,
    )
    await db.commit()
    return {"updated": len(subjects)}


@router.post("/report-cards/{report_card_id}/publish", response_model=ReportCardOut)
async def publish_report_card(
    report_card_id: uuid.UUID,
    user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> ReportCardOut:
    try:
        card = await report_card_service.publish_report_card(report_card_id, user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()

    from app.tasks.report_card_tasks import fan_out_report_card
    fan_out_report_card.delay(str(report_card_id))

    await db.refresh(card)
    return _card_out(card)


@router.get("/students/{student_id}/report-cards", response_model=list[ReportCardOut])
async def student_report_cards(
    student_id: uuid.UUID,
    _user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReportCardOut]:
    cards = await report_card_service.list_report_cards(db, student_id=student_id)
    return [_card_out(c) for c in cards]


@router.put("/report-cards/{report_card_id}/deliveries/{parent_id}/acknowledge")
async def admin_acknowledge(
    report_card_id: uuid.UUID,
    parent_id: uuid.UUID,
    _user: AdminUser = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    delivery = await report_card_service.acknowledge(report_card_id, parent_id, db, via="admin")
    await db.commit()
    return {
        "acknowledged_at": delivery.acknowledged_at.isoformat() if delivery.acknowledged_at else None,
        "via": delivery.acknowledged_via,
    }
