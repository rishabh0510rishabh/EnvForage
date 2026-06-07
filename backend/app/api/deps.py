"""
FastAPI dependency injectors.

Defines reusable dependency aliases used by API routes, including the
database session dependency shown in generated OpenAPI documentation.
"""

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db

# Type alias for dependency-injected DB session
DB = Annotated[AsyncSession, Depends(get_db)]

# ── JWT bearer scheme ─────────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Decode and validate the JWT Bearer token from the Authorization header.

    Returns the authenticated user's e-mail address on success.

    Raises:
        HTTP 401 — token is absent, malformed, expired, or has an invalid
                   signature.  A ``WWW-Authenticate: Bearer`` challenge header
                   is included so API clients know which scheme is required.

    Usage::

        @router.get("/protected")
        async def protected(email: CurrentUser) -> dict:
            return {"email": email}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "INVALID_TOKEN",
            "message": "Could not validate credentials.",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"],
        )
        email: str | None = payload.get("email")
        if not email:
            raise credentials_exception
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "TOKEN_EXPIRED",
                "message": "Access token has expired. Please sign in again.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception

    return email


# Type alias for dependency-injected authenticated user email
CurrentUser = Annotated[str, Depends(get_current_user)]


# ── Admin API key ─────────────────────────────────────────────────────────────


async def require_admin(
    x_admin_api_key: str | None = Header(
        default=None,
        description=(
            "Admin API key required for write operations. "
            "Set via the ADMIN_API_KEY environment variable."
        ),
    ),
) -> None:
    """
    Enforce admin API key authentication for protected write endpoints.

    Raises 503 if ADMIN_API_KEY is not configured so the application
    never silently accepts unauthenticated requests in production.
    Raises 401 if the key is absent or does not match.

    Uses a constant-time comparison (``secrets.compare_digest``) to
    prevent timing attacks that could reveal the correct key length.
    """
    settings = get_settings()

    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "ADMIN_KEY_NOT_CONFIGURED",
                    "message": (
                        "Admin API key is not configured on this server. "
                        "Set ADMIN_API_KEY in the environment before using "
                        "admin-only endpoints."
                    ),
                }
            },
        )

    if x_admin_api_key is None or not secrets.compare_digest(
        x_admin_api_key, settings.admin_api_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_ADMIN_KEY",
                    "message": "Missing or invalid X-Admin-API-Key header.",
                }
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )

