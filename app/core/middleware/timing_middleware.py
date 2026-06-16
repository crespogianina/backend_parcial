import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logger import get_logger

logger = get_logger("app.middleware.timing")

SLOW_REQUEST_THRESHOLD_MS = 500.0


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}ms"

        if elapsed_ms >= SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                "slow_request | %s %s | %.2fms",
                request.method,
                request.url.path,
                elapsed_ms,
            )
        else:
            logger.info(
                "request_timing | %s %s | %.2fms",
                request.method,
                request.url.path,
                elapsed_ms,
            )

        return response
