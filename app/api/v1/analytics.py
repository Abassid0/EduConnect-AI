from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_user import AdminUser
from app.services import analytics_service, referral_service
from app.utils.auth import get_current_user, require_role

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/volume")
async def conversation_volume(
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    return await analytics_service.get_conversation_volume(db, period, days)


@router.get("/response-time")
async def average_response_time(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    return await analytics_service.get_average_response_time(db, days)


@router.get("/resolution-rate")
async def bot_resolution_rate(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    return await analytics_service.get_bot_resolution_rate(db, days)


@router.get("/funnel")
async def conversion_funnel(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    return await analytics_service.get_conversion_funnel(db, days)


@router.get("/referrals")
async def referral_performance(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    return await analytics_service.get_referral_performance(db, days)


@router.get("/referrals/leaderboard")
async def referral_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    referrals = await referral_service.get_referral_leaderboard(db, limit)
    return [
        {
            "code": r.code,
            "referrer_type": r.referrer_type,
            "referrer_name": r.referrer_name,
            "total_registrations": r.total_registrations,
            "total_revenue": float(r.total_revenue),
            "commission_earned": float(r.commission_earned),
        }
        for r in referrals
    ]


@router.get("/ai")
async def ai_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    return await analytics_service.get_ai_analytics(db, days)


@router.get("/ai/top-queries")
async def ai_top_queries(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = Depends(get_current_user),
):
    return await analytics_service.get_ai_top_queries(db, days, limit)
