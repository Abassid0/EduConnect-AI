import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Numeric, case, cast, func, select, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_interaction import AIInteraction
from app.models.analytics_event import AnalyticsEvent

WAT = timezone(timedelta(hours=1))


async def track_event(
    event_type: str,
    db: AsyncSession,
    whatsapp_number: str | None = None,
    parent_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
    referral_code: str | None = None,
    properties: dict | None = None,
) -> AnalyticsEvent:
    event = AnalyticsEvent(
        id=uuid.uuid4(),
        event_type=event_type,
        whatsapp_number=whatsapp_number,
        parent_id=parent_id,
        student_id=student_id,
        conversation_id=conversation_id,
        referral_code=referral_code,
        properties=properties or {},
        created_at=datetime.now(WAT),
    )
    db.add(event)
    await db.flush()
    return event


async def get_conversation_volume(
    db: AsyncSession,
    period: str = "daily",
    days: int = 30,
) -> list[dict]:
    since = datetime.now(WAT) - timedelta(days=days)
    date_col = cast(AnalyticsEvent.created_at, Date)
    query = (
        select(date_col.label("date"), func.count().label("count"))
        .where(
            AnalyticsEvent.event_type == "conversation_start",
            AnalyticsEvent.created_at >= since,
        )
        .group_by(date_col)
        .order_by(date_col)
    )
    result = await db.execute(query)
    rows = result.all()

    if period == "weekly":
        return _aggregate_weekly(rows)
    if period == "monthly":
        return _aggregate_monthly(rows)
    return [{"date": str(r.date), "count": r.count} for r in rows]


def _aggregate_weekly(rows) -> list[dict]:
    weeks: dict[str, int] = {}
    for r in rows:
        d = r.date
        week_start = d - timedelta(days=d.weekday())
        key = str(week_start)
        weeks[key] = weeks.get(key, 0) + r.count
    return [{"week_start": k, "count": v} for k, v in weeks.items()]


def _aggregate_monthly(rows) -> list[dict]:
    months: dict[str, int] = {}
    for r in rows:
        key = r.date.strftime("%Y-%m")
        months[key] = months.get(key, 0) + r.count
    return [{"month": k, "count": v} for k, v in months.items()]


async def get_conversion_funnel(
    db: AsyncSession, days: int = 30
) -> dict:
    since = datetime.now(WAT) - timedelta(days=days)
    stages = [
        "conversation_start",
        "registration_start",
        "registration_complete",
        "payment_init",
        "payment_complete",
    ]
    counts = {}
    for stage in stages:
        result = await db.execute(
            select(func.count())
            .where(
                AnalyticsEvent.event_type == stage,
                AnalyticsEvent.created_at >= since,
            )
        )
        counts[stage] = result.scalar() or 0

    funnel = []
    for i, stage in enumerate(stages):
        entry = {"stage": stage, "count": counts[stage]}
        if i > 0 and counts[stages[i - 1]] > 0:
            entry["drop_off_pct"] = round(
                (1 - counts[stage] / counts[stages[i - 1]]) * 100, 1
            )
        else:
            entry["drop_off_pct"] = 0.0
        funnel.append(entry)
    return {"funnel": funnel, "period_days": days}


async def get_bot_resolution_rate(
    db: AsyncSession, days: int = 30
) -> dict:
    since = datetime.now(WAT) - timedelta(days=days)
    total_result = await db.execute(
        select(func.count())
        .where(
            AnalyticsEvent.event_type == "conversation_start",
            AnalyticsEvent.created_at >= since,
        )
    )
    total = total_result.scalar() or 0

    escalated_result = await db.execute(
        select(func.count())
        .where(
            AnalyticsEvent.event_type == "support_escalation",
            AnalyticsEvent.created_at >= since,
        )
    )
    escalated = escalated_result.scalar() or 0

    bot_resolved = total - escalated if total > escalated else 0
    rate = round((bot_resolved / total) * 100, 1) if total > 0 else 0.0

    return {
        "total_conversations": total,
        "escalated": escalated,
        "bot_resolved": bot_resolved,
        "resolution_rate_pct": rate,
        "period_days": days,
    }


async def get_average_response_time(
    db: AsyncSession, days: int = 30
) -> dict:
    since = datetime.now(WAT) - timedelta(days=days)
    result = await db.execute(
        select(func.avg(
            cast(AnalyticsEvent.properties["response_time_seconds"].astext, Numeric)
        ))
        .where(
            AnalyticsEvent.event_type == "agent_response",
            AnalyticsEvent.created_at >= since,
        )
    )
    avg_seconds = result.scalar()
    return {
        "avg_response_seconds": round(float(avg_seconds), 1) if avg_seconds else None,
        "period_days": days,
    }


async def get_referral_performance(
    db: AsyncSession, days: int = 90
) -> list[dict]:
    since = datetime.now(WAT) - timedelta(days=days)
    result = await db.execute(
        select(
            AnalyticsEvent.referral_code,
            func.count().label("registrations"),
            func.count(
                case(
                    (AnalyticsEvent.event_type == "payment_complete", 1),
                )
            ).label("payments"),
        )
        .where(
            AnalyticsEvent.referral_code.isnot(None),
            AnalyticsEvent.event_type.in_(["registration_complete", "payment_complete"]),
            AnalyticsEvent.created_at >= since,
        )
        .group_by(AnalyticsEvent.referral_code)
        .order_by(func.count().desc())
    )
    return [
        {
            "referral_code": r.referral_code,
            "registrations": r.registrations,
            "payments": r.payments,
        }
        for r in result.all()
    ]


async def get_events(
    db: AsyncSession,
    event_type: str | None = None,
    days: int = 30,
    limit: int = 100,
) -> list[AnalyticsEvent]:
    since = datetime.now(WAT) - timedelta(days=days)
    query = (
        select(AnalyticsEvent)
        .where(AnalyticsEvent.created_at >= since)
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(limit)
    )
    if event_type:
        query = query.where(AnalyticsEvent.event_type == event_type)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_ai_analytics(db: AsyncSession, days: int = 30) -> dict:
    since = datetime.now(WAT) - timedelta(days=days)

    total_result = await db.execute(
        select(func.count())
        .select_from(AIInteraction)
        .where(AIInteraction.created_at >= since)
    )
    total = total_result.scalar() or 0

    escalated_result = await db.execute(
        select(func.count())
        .select_from(AIInteraction)
        .where(AIInteraction.created_at >= since, AIInteraction.escalated.is_(True))
    )
    escalated = escalated_result.scalar() or 0

    avg_confidence_result = await db.execute(
        select(func.avg(AIInteraction.confidence_score))
        .where(AIInteraction.created_at >= since)
    )
    avg_confidence = avg_confidence_result.scalar()

    avg_response_result = await db.execute(
        select(func.avg(AIInteraction.response_time_ms))
        .where(AIInteraction.created_at >= since)
    )
    avg_response_ms = avg_response_result.scalar()

    resolved = total - escalated
    resolution_rate = round((resolved / total) * 100, 1) if total > 0 else 0.0

    return {
        "total_queries": total,
        "resolved": resolved,
        "escalated": escalated,
        "resolution_rate_pct": resolution_rate,
        "avg_confidence": round(float(avg_confidence), 2) if avg_confidence else None,
        "avg_response_ms": round(float(avg_response_ms)) if avg_response_ms else None,
        "period_days": days,
    }


async def get_ai_top_queries(db: AsyncSession, days: int = 30, limit: int = 10) -> list[dict]:
    since = datetime.now(WAT) - timedelta(days=days)

    result = await db.execute(
        select(AIInteraction)
        .where(AIInteraction.created_at >= since)
        .order_by(AIInteraction.created_at.desc())
        .limit(200)
    )
    interactions = result.scalars().all()

    query_counts: dict[str, dict] = {}
    for i in interactions:
        key = i.user_query.lower().strip()[:100]
        if key not in query_counts:
            query_counts[key] = {
                "query": i.user_query[:100],
                "count": 0,
                "avg_confidence": 0.0,
                "escalated_count": 0,
            }
        query_counts[key]["count"] += 1
        query_counts[key]["avg_confidence"] += i.confidence_score
        if i.escalated:
            query_counts[key]["escalated_count"] += 1

    for entry in query_counts.values():
        entry["avg_confidence"] = round(entry["avg_confidence"] / entry["count"], 2)

    sorted_queries = sorted(query_counts.values(), key=lambda x: x["count"], reverse=True)
    return sorted_queries[:limit]
