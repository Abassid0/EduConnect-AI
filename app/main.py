import logging

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.v1 import router as v1_router
from app.config import settings
from app.database import async_session_factory
from app.middleware.audit_log import AuditLogMiddleware
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.rate_limit import limiter

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    force=True,
)

app = FastAPI(
    title="Edpassare WhatsApp Platform",
    description="WhatsApp-first customer engagement platform for Edpassare",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(AuditLogMiddleware)
app.add_middleware(CorrelationIdMiddleware)
cors_origins = ["*"] if settings.APP_ENV == "development" else (
    [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if settings.CORS_ORIGINS else []
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/health")
async def health() -> dict:
    checks: dict[str, str] = {}
    healthy = True

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception:
        checks["database"] = "unavailable"
        healthy = False

    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "connected"
    except Exception:
        checks["redis"] = "unavailable"
        healthy = False

    if settings.WA_ACCESS_TOKEN and settings.WA_PHONE_NUMBER_ID:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"https://graph.facebook.com/{settings.WA_API_VERSION}/{settings.WA_PHONE_NUMBER_ID}",
                    headers={"Authorization": f"Bearer {settings.WA_ACCESS_TOKEN}"},
                )
                checks["whatsapp"] = "connected" if resp.status_code == 200 else "degraded"
                if resp.status_code != 200:
                    healthy = False
        except Exception:
            checks["whatsapp"] = "unreachable"
            healthy = False
    else:
        checks["whatsapp"] = "not_configured"

    return {
        "status": "healthy" if healthy else "degraded",
        "version": "1.0.0",
        "checks": checks,
    }
