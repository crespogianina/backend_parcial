from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logger import get_logger

logger = get_logger("app.middleware.logging")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        client = request.client.host if request.client else "unknown"
        logger.info(
            "request_started | %s %s | client=%s",
            request.method,
            request.url.path,
            client,
        )

        response = await call_next(request)

        logger.info(
            "request_completed | %s %s → %d",
            request.method,
            request.url.path,
            response.status_code,
        )

        return response
