import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.correlation import get_correlation_id

logger = logging.getLogger("audit")


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "[%s] %s %s %s %.1fms",
            get_correlation_id(),
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
