import random
import string
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral import Referral


def _generate_code(prefix: str = "EDP") -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=6))
    return f"{prefix}-{suffix}"


async def create_referral(
    referrer_type: str,
    db: AsyncSession,
    referrer_name: str | None = None,
    referrer_whatsapp: str | None = None,
    referrer_email: str | None = None,
    parent_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
    commission_rate: Decimal = Decimal("0.00"),
    metadata: dict | None = None,
) -> Referral:
    code = _generate_code()
    existing = await db.execute(
        select(Referral).where(Referral.code == code)
    )
    while existing.scalar_one_or_none() is not None:
        code = _generate_code()
        existing = await db.execute(
            select(Referral).where(Referral.code == code)
        )

    referral = Referral(
        id=uuid.uuid4(),
        code=code,
        referrer_type=referrer_type,
        referrer_name=referrer_name,
        referrer_whatsapp=referrer_whatsapp,
        referrer_email=referrer_email,
        parent_id=parent_id,
        agent_id=agent_id,
        commission_rate=commission_rate,
        metadata_=metadata or {},
    )
    db.add(referral)
    await db.flush()
    return referral


async def get_referral_by_code(
    code: str, db: AsyncSession
) -> Referral | None:
    result = await db.execute(
        select(Referral).where(Referral.code == code.upper(), Referral.is_active == True)
    )
    return result.scalar_one_or_none()


async def validate_referral_code(
    code: str, db: AsyncSession
) -> Referral | None:
    return await get_referral_by_code(code, db)


async def record_referral_registration(
    referral: Referral,
    payment_amount: Decimal,
    db: AsyncSession,
) -> None:
    referral.total_registrations += 1
    referral.total_revenue += payment_amount
    if referral.commission_rate > 0:
        referral.commission_earned += payment_amount * referral.commission_rate / 100
    await db.flush()


async def record_referral_payment(
    referral_code: str,
    payment_amount: Decimal,
    db: AsyncSession,
) -> None:
    referral = await get_referral_by_code(referral_code, db)
    if not referral:
        return
    referral.total_revenue += payment_amount
    if referral.commission_rate > 0:
        referral.commission_earned += payment_amount * referral.commission_rate / 100
    await db.flush()


async def get_referrals(
    db: AsyncSession,
    referrer_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Referral]:
    query = select(Referral).order_by(Referral.created_at.desc())
    if referrer_type:
        query = query.where(Referral.referrer_type == referrer_type)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_referral_leaderboard(
    db: AsyncSession, limit: int = 20
) -> list[Referral]:
    result = await db.execute(
        select(Referral)
        .where(Referral.is_active == True)
        .order_by(Referral.total_registrations.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
