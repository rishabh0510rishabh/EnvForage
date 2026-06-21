"""Authentication endpoints — /signup, /signin, /me.

Rate-limiting:  /signup and /signin are protected by ``auth_rate_limit``
(configurable via ``settings.rate_limit_auth_rpm``, default 20 rpm) to
prevent brute-force and credential-stuffing attacks.

JWT validation: the /me endpoint demonstrates the ``CurrentUser`` dependency
that other routes should use to require an authenticated user.
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentUser
from app.config import get_settings
from app.middleware.rate_limit import auth_rate_limit
from app.services.user_repository import UserRepository

router = APIRouter()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Request schemas ────────────────────────────────────────────────────────────


class RegData(BaseModel):
    fname: str
    lname: str
    email: EmailStr
    password: str = Field(
        min_length=12,
        description="Must be at least 12 characters with uppercase, lowercase, digit, and symbol",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce strong password requirements to prevent dictionary attacks.

        Requirements:
        - Minimum 12 characters (strong entropy)
        - At least one uppercase letter (A-Z)
        - At least one lowercase letter (a-z)
        - At least one digit (0-9)
        - At least one special character

        bcrypt also has a hard 72-byte limit on UTF-8 encoded passwords.
        Two different passwords that share the same first 72 bytes would
        both authenticate successfully. We reject longer passwords early
        to avoid silent data loss and auth ambiguity.
        """
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes (UTF-8 encoded)")

        if not any(c.isupper() for c in v):
            raise ValueError(
                "Password must contain at least one uppercase letter (A-Z)"
            )

        if not any(c.islower() for c in v):
            raise ValueError(
                "Password must contain at least one lowercase letter (a-z)"
            )

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit (0-9)")

        special_chars = "!@#$%^&*()-_=+[]{}|;:',.<>?/~`"
        if not any(c in special_chars for c in v):
            raise ValueError(
                f"Password must contain at least one special character from: {special_chars}"
            )

        return v


class LoginData(BaseModel):
    email: EmailStr
    password: str


# ── Response schemas ───────────────────────────────────────────────────────────


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    token: str
    email: EmailStr


class MeResponse(BaseModel):
    email: EmailStr


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post(
    "/signup",
    response_model=MessageResponse,
    summary="Register a new user account",
    responses={
        400: {"description": "Email already registered"},
        422: {
            "description": "Validation error (password too weak/long, invalid email)"
        },
        429: {"description": "Rate limit exceeded"},
    },
)
async def signup(
    data: RegData,
    db: DB,
    _rate_limit: None = Depends(auth_rate_limit),
) -> MessageResponse:
    """Create a new user account.

    Rate-limited via ``auth_rate_limit`` (default 20 rpm, configurable
    via ``settings.rate_limit_auth_rpm``) to prevent mass account creation
    and credential-stuffing attacks.
    """
    repo = UserRepository(db)
    if await repo.user_exists(data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    try:
        await repo.create_user(
            email=data.email,
            fname=data.fname,
            lname=data.lname,
            hashed_password=pwd.hash(data.password),
        )
    except IntegrityError:
        # Guard against check-then-insert race: two concurrent requests can
        # both pass user_exists() above, but the DB unique constraint on email
        # will reject the second insert.  Return 400 instead of leaking a 500.
        raise HTTPException(status_code=400, detail="Email already registered")
    return MessageResponse(message="Account created successfully")


@router.post(
    "/signin",
    response_model=TokenResponse,
    summary="Sign in and receive a JWT access token",
    responses={
        401: {"description": "Invalid email or password"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def signin(
    data: LoginData,
    db: DB,
    _rate_limit: None = Depends(auth_rate_limit),
) -> TokenResponse:
    """Authenticate with email + password and receive a signed JWT.

    Rate-limited via ``auth_rate_limit`` (default 20 rpm, configurable
    via ``settings.rate_limit_auth_rpm``) to prevent brute-force password
    attacks. The returned token must be sent as
    ``Authorization: Bearer <token>`` on subsequent protected requests.
    """
    repo = UserRepository(db)
    user = await repo.get_user_by_email(data.email)
    if not user or not pwd.verify(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    exp = datetime.now(UTC) + timedelta(hours=24)
    settings = get_settings()
    token = jwt.encode(
        {"email": data.email, "exp": exp}, settings.secret_key, algorithm="HS256"
    )
    return TokenResponse(token=token, email=data.email)


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Return the currently authenticated user's email",
    responses={
        401: {"description": "Missing, expired, or invalid JWT token"},
    },
)
async def me(current_user: CurrentUser) -> MeResponse:
    """Return the email of the currently authenticated user.

    Requires a valid ``Authorization: Bearer <token>`` header.
    Use this as the canonical example of how other endpoints should
    require authentication via the ``CurrentUser`` dependency.
    """
    return MeResponse(email=current_user)
