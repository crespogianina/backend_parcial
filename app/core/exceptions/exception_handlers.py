from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import get_logger

logger = get_logger("app.exceptions")


def _error_response(status_code: int, message: str, detail=None) -> JSONResponse:
    body = {"error": message, "detail": detail if detail is not None else message}
    return JSONResponse(status_code=status_code, content=body)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(
        "http_exception | %s %s → %d",
        request.method,
        request.url.path,
        exc.status_code,
    )
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return _error_response(exc.status_code, message)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(loc) for loc in e["loc"]), "msg": e["msg"]}
        for e in exc.errors()
    ]
    logger.warning(
        "validation_error | %s %s | %s",
        request.method,
        request.url.path,
        errors,
    )
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Error de validación en los datos enviados.",
        errors,
    )


async def sqlalchemy_exception_handler(request: Request, exc: IntegrityError):
    logger.error(
        "db_integrity_error | %s %s | %s",
        request.method,
        request.url.path,
        str(exc.orig),
    )
    return _error_response(
        status.HTTP_409_CONFLICT,
        "Conflicto en la base de datos. El recurso ya existe o viola una restricción.",
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception | %s %s | %s",
        request.method,
        request.url.path,
        repr(exc),
    )
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Error interno del servidor.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
