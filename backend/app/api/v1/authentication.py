from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB
from app.config import get_settings
from app.services.user_repository import UserRepository

router = APIRouter()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Request schemas ────────────────────────────────────────────────────────────

class RegData(BaseModel):
    fname: str
    lname: str
    email: EmailStr
    password: str = Field(min_length=6, description="Must be at least 6 characters")

    @field_validator("password")
    @classmethod
    def password_max_bytes(cls, v: str) -> str:
        """Enforce bcrypt's hard 72-byte limit on the UTF-8 encoded password.

        bcrypt silently truncates inputs longer than 72 bytes, meaning two
        different passwords that share the same first 72 bytes would both
        authenticate successfully.  We reject them early to avoid silent
        data loss and auth ambiguity.  Byte length is checked (not character
        count) so non-ASCII passwords are handled correctly.
        """
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes")
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


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=MessageResponse)
async def signup(data: RegData, db: DB) -> MessageResponse:
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


@router.post("/signin", response_model=TokenResponse)
async def signin(data: LoginData, db: DB) -> TokenResponse:
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


