"""Global exception handlers for FastAPI application."""

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AIServiceUnavailableError,
    AppError,
    ConflictError,
    EntityNotFoundError,
    InternalServerError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | list[dict[str, object]],
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": {
                "error": {
                    "code": code,
                    "message": message,
                    "details": details,
                }
            }
        },
    )


def _redact_validation_errors(
    errors: list[Any],
) -> list[dict[str, object]]:
    """Strip user-supplied input values from validation errors before
    logging or returning them to the client."""
    redacted: list[dict[str, object]] = []
    for error in errors:
        loc = error.get("loc", [])
        redacted.append(
            {
                "type": error.get("type"),
                "loc": [str(item) for item in loc],
                "msg": error.get("msg"),
            }
        )
    return redacted


def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide exception handlers."""

    async def app_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, AppError)
        logger.error("%s: %s", exc.error_code, exc.message)
        return _error_response(
            exc.status_code, exc.error_code, exc.message, exc.details or {}
        )

    for exc_class in (
        EntityNotFoundError,
        ConflictError,
        ValidationError,
        InternalServerError,
        AIServiceUnavailableError,
        AppError,
    ):
        app.add_exception_handler(exc_class, app_exception_handler)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        redacted = _redact_validation_errors(list(exc.errors()))
        logger.warning("Validation error: %s", redacted)
        return _error_response(
            422, "VALIDATION_ERROR", "Request validation failed.", redacted
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        reference_id = str(uuid.uuid4())
        logger.exception("Unhandled exception [%s]: %s", reference_id, exc)
        return _error_response(
            500,
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred.",
            {"reference_id": reference_id},
        )
