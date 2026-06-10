from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import settings

_lock = Lock()
_attempts: dict[str, list[datetime]] = {}


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _window() -> timedelta:
    return timedelta(minutes=settings.AUTH_RATE_LIMIT_WINDOW_MINUTES)


def _prune(timestamps: list[datetime], now: datetime) -> list[datetime]:
    cutoff = now - _window()
    return [ts for ts in timestamps if ts > cutoff]


def _retry_after_seconds(oldest: datetime, now: datetime) -> int:
    remaining = (oldest + _window()) - now
    return max(1, int(remaining.total_seconds()))


def check_auth_rate_limit(request: Request) -> None:
    ip = get_client_ip(request)
    now = datetime.now(timezone.utc)

    with _lock:
        state = _attempts.setdefault(ip, [])
        state[:] = _prune(state, now)

        if len(state) >= settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS:
            oldest = min(state)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos fallidos. Intente nuevamente más tarde.",
                headers={
                    "Retry-After": str(_retry_after_seconds(oldest, now)),
                },
            )


def record_auth_failure(request: Request) -> None:
    ip = get_client_ip(request)
    now = datetime.now(timezone.utc)

    with _lock:
        state = _attempts.setdefault(ip, [])
        state[:] = _prune(state, now)
        state.append(now)
