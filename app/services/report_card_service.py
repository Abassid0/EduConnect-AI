import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_card import ReportCard, ReportCardDelivery, ReportCardSubject

logger = logging.getLogger(__name__)


async def create_report_card(
    student_id: uuid.UUID,
    academic_term: str,
    db: AsyncSession,
    overall_grade: str | None = None,
    overall_score=None,
    position_in_class: int | None = None,
    class_size: int | None = None,
    teacher_comment: str | None = None,
    created_by: uuid.UUID | None = None,
) -> ReportCard:
    existing = await db.execute(
        select(ReportCard).where(
            ReportCard.student_id == student_id,
            ReportCard.academic_term == academic_term,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"A report card for this student and term already exists.")

    card = ReportCard(
        id=uuid.uuid4(),
        student_id=student_id,
        academic_term=academic_term,
        overall_grade=overall_grade,
        overall_score=overall_score,
        position_in_class=position_in_class,
        class_size=class_size,
        teacher_comment=teacher_comment,
        status="draft",
    )
    db.add(card)
    await db.flush()
    await db.refresh(card)
    return card


async def add_subject(
    report_card_id: uuid.UUID,
    subject_name: str,
    db: AsyncSession,
    score=None,
    grade: str | None = None,
    teacher_comment: str | None = None,
    sort_order: int = 0,
) -> ReportCardSubject:
    subject = ReportCardSubject(
        id=uuid.uuid4(),
        report_card_id=report_card_id,
        subject_name=subject_name,
        score=score,
        grade=grade,
        teacher_comment=teacher_comment,
        sort_order=sort_order,
    )
    db.add(subject)
    await db.flush()
    return subject


async def replace_subjects(
    report_card_id: uuid.UUID,
    subjects: list[dict],
    db: AsyncSession,
) -> list[ReportCardSubject]:
    await db.execute(
        delete(ReportCardSubject).where(ReportCardSubject.report_card_id == report_card_id)
    )
    await db.flush()

    created = []
    for i, s in enumerate(subjects):
        subj = ReportCardSubject(
            id=uuid.uuid4(),
            report_card_id=report_card_id,
            subject_name=s["subject_name"],
            score=s.get("score"),
            grade=s.get("grade"),
            teacher_comment=s.get("teacher_comment"),
            sort_order=s.get("sort_order", i),
        )
        db.add(subj)
        created.append(subj)
    await db.flush()
    return created


async def get_report_card(report_card_id: uuid.UUID, db: AsyncSession) -> ReportCard | None:
    result = await db.execute(select(ReportCard).where(ReportCard.id == report_card_id))
    return result.scalar_one_or_none()


async def list_report_cards(
    db: AsyncSession,
    student_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ReportCard]:
    query = select(ReportCard).order_by(ReportCard.created_at.desc()).limit(limit).offset(offset)
    if student_id:
        query = query.where(ReportCard.student_id == student_id)
    if status:
        query = query.where(ReportCard.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())


async def publish_report_card(
    report_card_id: uuid.UUID,
    published_by: uuid.UUID,
    db: AsyncSession,
) -> ReportCard:
    from app.models.student import Student

    card = await get_report_card(report_card_id, db)
    if not card:
        raise ValueError("Report card not found.")
    if card.status != "draft":
        raise ValueError("Only draft report cards can be published.")

    card.status = "published"
    card.published_at = datetime.now(timezone.utc)
    card.published_by = published_by
    await db.flush()

    # Find the student's parent and create delivery rows
    student_result = await db.execute(select(Student).where(Student.id == card.student_id))
    student = student_result.scalar_one_or_none()
    if student:
        existing_delivery = await db.execute(
            select(ReportCardDelivery).where(
                ReportCardDelivery.report_card_id == report_card_id,
                ReportCardDelivery.parent_id == student.parent_id,
            )
        )
        if not existing_delivery.scalar_one_or_none():
            delivery = ReportCardDelivery(
                id=uuid.uuid4(),
                report_card_id=report_card_id,
                parent_id=student.parent_id,
            )
            db.add(delivery)

    await db.flush()
    await db.refresh(card)
    return card


async def get_unacknowledged_for_parent(
    parent_id: uuid.UUID,
    db: AsyncSession,
) -> list[ReportCard]:
    result = await db.execute(
        select(ReportCard)
        .join(
            ReportCardDelivery,
            (ReportCardDelivery.report_card_id == ReportCard.id)
            & (ReportCardDelivery.parent_id == parent_id),
        )
        .where(
            ReportCard.status == "published",
            ReportCardDelivery.acknowledged_at.is_(None),
        )
        .order_by(ReportCard.published_at.asc())
    )
    return list(result.scalars().all())


async def acknowledge(
    report_card_id: uuid.UUID,
    parent_id: uuid.UUID,
    db: AsyncSession,
    via: str = "whatsapp",
) -> ReportCardDelivery:
    result = await db.execute(
        select(ReportCardDelivery).where(
            ReportCardDelivery.report_card_id == report_card_id,
            ReportCardDelivery.parent_id == parent_id,
        )
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        delivery = ReportCardDelivery(
            id=uuid.uuid4(),
            report_card_id=report_card_id,
            parent_id=parent_id,
        )
        db.add(delivery)

    delivery.acknowledged_at = datetime.now(timezone.utc)
    delivery.acknowledged_via = via
    await db.flush()
    return delivery


async def get_delivery_summary(report_card_id: uuid.UUID, db: AsyncSession) -> dict:
    card = await get_report_card(report_card_id, db)
    if not card:
        return {}

    deliveries = card.deliveries
    total = len(deliveries)
    delivered_count = sum(1 for d in deliveries if d.delivered_at is not None)
    acknowledged_count = sum(1 for d in deliveries if d.acknowledged_at is not None)

    return {
        "total_parents": total,
        "delivered_count": delivered_count,
        "acknowledged_count": acknowledged_count,
        "deliveries": [
            {
                "parent_id": str(d.parent_id),
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
                "acknowledged_at": d.acknowledged_at.isoformat() if d.acknowledged_at else None,
                "acknowledged_via": d.acknowledged_via,
            }
            for d in deliveries
        ],
    }


def format_report_card_message(card: ReportCard, student_name: str = "") -> str:
    lines = [f"*Report Card — {student_name or 'Student'} | {card.academic_term}*\n"]

    if card.position_in_class and card.class_size:
        lines.append(f"Position: {card.position_in_class} of {card.class_size}")
    elif card.position_in_class:
        lines.append(f"Position: {card.position_in_class}")

    subjects = sorted(card.subjects, key=lambda s: (s.sort_order, s.subject_name))
    if subjects:
        lines.append("\n📚 *Subjects:*")
        for s in subjects:
            parts = [s.subject_name.ljust(20)]
            if s.score is not None:
                parts.append(str(int(s.score) if s.score == int(s.score) else s.score).rjust(5))
            if s.grade:
                parts.append(s.grade.rjust(4))
            lines.append("  " + "  ".join(parts))

    if card.overall_grade or card.overall_score:
        grade_parts = []
        if card.overall_grade:
            grade_parts.append(card.overall_grade)
        if card.overall_score is not None:
            grade_parts.append(f"{card.overall_score}")
        lines.append(f"\nOverall: {' — '.join(grade_parts)}")

    if card.teacher_comment:
        lines.append(f"\n_{card.teacher_comment}_")

    return "\n".join(lines)
