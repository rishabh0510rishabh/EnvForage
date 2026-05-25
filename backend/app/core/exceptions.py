from fastapi import status

__all__ = [
    "AppError",
    "EntityNotFoundError",
    "ConflictError",
    "ValidationError",
    "InternalServerError",
    "AIServiceUnavailableError",
]


class AppError(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int,
        details: dict[str, object] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class EntityNotFoundError(AppError):
    """Raised when a requested entity does not exist."""

    def __init__(
        self,
        resource: str,
        error_code: str = "ENTITY_NOT_FOUND",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=f"{resource} not found.",
            error_code=error_code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(AppError):
    """Raised for duplicate/conflicting resources."""

    def __init__(
        self,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="CONFLICT_ERROR",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ValidationError(AppError):
    """Raised for validation failures."""

    def __init__(
        self,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class InternalServerError(AppError):
    """Raised for unexpected internal application errors."""

    def __init__(
        self,
        message: str = "Internal server error.",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="INTERNAL_SERVER_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class AIServiceUnavailableError(AppError):
    """Raised when AI provider/service is unavailable."""

    def __init__(
        self,
        provider: str | None = None,
        reason: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        provider_name = provider or "unknown"

        message = (
            f"AI service unavailable ({provider_name})."
            if not reason
            else f"AI service unavailable ({provider_name}): {reason}"
        )

        merged_details: dict[str, object] = {
            "provider": provider,
            "reason": reason,
            **(details or {}),
        }

        super().__init__(
            message=message,
            error_code="AI_SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=merged_details,
        )
