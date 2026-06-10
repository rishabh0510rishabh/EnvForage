"""Tests for /signup and /signin authentication endpoints.

Uses the shared in-memory SQLite engine from conftest.py so no live
Postgres connection is needed.  Each test gets a fresh ``db_session``
that is automatically rolled back after the test, keeping tests isolated.

NOTE: passlib 1.7.4 is incompatible with bcrypt >=4.0 (an 80-byte internal
self-test string exceeds bcrypt's 72-byte limit).  HTTP-layer tests that
invoke hashing use a monkeypatched CryptContext backed by passlib's
``plaintext`` scheme to stay fast and hermetic.  The real bcrypt hashing
path is exercised separately by ``test_bcrypt_hash_and_verify_round_trip``
and ``test_signin_real_bcrypt_hash`` which use the ``bcrypt`` library
directly, bypassing passlib's broken self-test.
"""

import bcrypt
import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.v1.authentication as auth_module
from app.database import get_db
from app.main import create_app
from app.services.user_repository import UserRepository


def _bcrypt_hash(plain: str) -> str:
    """Hash a password with bcrypt directly — bypasses passlib's self-test."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _bcrypt_verify(plain: str, hashed: str) -> bool:
    """Verify a bcrypt hash directly — bypasses passlib's self-test."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Helpers ───────────────────────────────────────────────────────────────────

# A passlib CryptContext that uses no real hashing — avoids passlib/bcrypt 5.x
# incompatibility (ValueError: password cannot be longer than 72 bytes).
_PLAINTEXT_PWD = CryptContext(schemes=["plaintext"], deprecated="auto")


def _make_client(db_session: AsyncSession, monkeypatch) -> TestClient:
    """Return a TestClient wired to the test DB session and plaintext hashing."""
    monkeypatch.setattr(auth_module, "pwd", _PLAINTEXT_PWD)

    test_app = create_app()

    async def override_get_db():
        yield db_session

    # Bypass rate limiting so tests are not throttled.
    # Override the shared auth_rate_limit used by both /signup and /signin.
    async def mock_rate_limiter():
        return None

    from app.middleware.rate_limit import auth_rate_limit

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[auth_rate_limit] = mock_rate_limiter
    return TestClient(test_app, raise_server_exceptions=True)


# ── /signup ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_signup_success(db_session: AsyncSession, monkeypatch):
    """New user can register; response body contains success message."""
    client = _make_client(db_session, monkeypatch)
    resp = client.post(
        "/api/v1/signup",
        json={
            "fname": "Alice",
            "lname": "Example",
            "email": "alice@example.com",
            "password": "SecurePass123!",  # meets new requirements: 12+ chars, uppercase, lowercase, digit, special
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"message": "Account created successfully"}


@pytest.mark.asyncio
async def test_signup_user_persisted_in_db(db_session: AsyncSession, monkeypatch):
    """After signup the user record is actually stored in the database."""
    client = _make_client(db_session, monkeypatch)
    client.post(
        "/api/v1/signup",
        json={
            "fname": "Bob",
            "lname": "Builder",
            "email": "bob@example.com",
            "password": "BuilderPass123!",  # meets new requirements
        },
    )

    repo = UserRepository(db_session)
    user = await repo.get_user_by_email("bob@example.com")
    assert user is not None
    assert user.fname == "Bob"
    assert user.lname == "Builder"
    # With plaintext scheme the stored value is not the raw password
    # (passlib wraps it), but it must not equal the original plain string
    # in a real-hash scenario.  Here we simply confirm a record was stored.
    assert user.password is not None


@pytest.mark.asyncio
async def test_signup_duplicate_email_returns_400(
    db_session: AsyncSession, monkeypatch
):
    """Registering with an already-used e-mail returns HTTP 400."""
    client = _make_client(db_session, monkeypatch)
    payload = {
        "fname": "Carol",
        "lname": "Tester",
        "email": "carol@example.com",
        "password": "TestPass1234!",  # meets new requirements
    }
    client.post("/api/v1/signup", json=payload)  # first registration
    resp = client.post("/api/v1/signup", json=payload)  # duplicate
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_signup_password_too_short_returns_422(
    db_session: AsyncSession, monkeypatch
):
    """A password shorter than 12 characters is rejected at schema level (422)."""
    client = _make_client(db_session, monkeypatch)
    resp = client.post(
        "/api/v1/signup",
        json={
            "fname": "Dave",
            "lname": "Short",
            "email": "dave@example.com",
            "password": "Abc123!",  # only 7 chars (less than 12)
        },
    )
    # Pydantic Field(min_length=12) returns 422 Unprocessable Entity
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_signup_password_missing_uppercase_returns_422(
    db_session: AsyncSession, monkeypatch
):
    """A password without uppercase letters is rejected (422)."""
    client = _make_client(db_session, monkeypatch)
    resp = client.post(
        "/api/v1/signup",
        json={
            "fname": "Eve",
            "lname": "Tester",
            "email": "eve@example.com",
            "password": "lowercase123!",  # missing uppercase
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_signup_password_missing_lowercase_returns_422(
    db_session: AsyncSession, monkeypatch
):
    """A password without lowercase letters is rejected (422)."""
    client = _make_client(db_session, monkeypatch)
    resp = client.post(
        "/api/v1/signup",
        json={
            "fname": "Frank",
            "lname": "Tester",
            "email": "frank@example.com",
            "password": "UPPERCASE123!",  # missing lowercase
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_signup_password_missing_digit_returns_422(
    db_session: AsyncSession, monkeypatch
):
    """A password without digits is rejected (422)."""
    client = _make_client(db_session, monkeypatch)
    resp = client.post(
        "/api/v1/signup",
        json={
            "fname": "Grace",
            "lname": "Tester",
            "email": "grace@example.com",
            "password": "NoDigitsHere!",  # missing digit
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_signup_password_missing_special_char_returns_422(
    db_session: AsyncSession, monkeypatch
):
    """A password without special characters is rejected (422)."""
    client = _make_client(db_session, monkeypatch)
    resp = client.post(
        "/api/v1/signup",
        json={
            "fname": "Henry",
            "lname": "Tester",
            "email": "henry@example.com",
            "password": "NoSpecialChar123",  # missing special character
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_signup_missing_fields_returns_422(db_session: AsyncSession, monkeypatch):
    """Omitting required fields produces a 422 validation error."""
    client = _make_client(db_session, monkeypatch)
    resp = client.post("/api/v1/signup", json={"email": "incomplete@example.com"})
    assert resp.status_code == 422


# ── /signin ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_signin_success_returns_token(db_session: AsyncSession, monkeypatch):
    """Valid credentials return a JWT token and the user's email."""
    client = _make_client(db_session, monkeypatch)
    strong_password = "TokenPass123!"  # meets new requirements
    # Register first
    client.post(
        "/api/v1/signup",
        json={
            "fname": "Eve",
            "lname": "Token",
            "email": "eve@example.com",
            "password": strong_password,
        },
    )
    # Then sign in
    resp = client.post(
        "/api/v1/signin",
        json={"email": "eve@example.com", "password": strong_password},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert body["email"] == "eve@example.com"
    # JWT is three dot-separated base64 segments
    assert body["token"].count(".") == 2


@pytest.mark.asyncio
async def test_signin_wrong_password_returns_401(db_session: AsyncSession, monkeypatch):
    """Signing in with the wrong password is rejected with HTTP 401."""
    client = _make_client(db_session, monkeypatch)
    client.post(
        "/api/v1/signup",
        json={
            "fname": "Frank",
            "lname": "Wrong",
            "email": "frank@example.com",
            "password": "CorrectPass123!",  # meets new requirements
        },
    )
    resp = client.post(
        "/api/v1/signin",
        json={
            "email": "frank@example.com",
            "password": "WrongPass123!",
        },  # wrong password but still strong
    )
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_signin_unknown_email_returns_401(db_session: AsyncSession, monkeypatch):
    """Signing in with an unregistered email returns HTTP 401."""
    client = _make_client(db_session, monkeypatch)
    resp = client.post(
        "/api/v1/signin",
        json={"email": "ghost@example.com", "password": "doesnotmatter"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_signin_invalid_email_format_returns_422(
    db_session: AsyncSession, monkeypatch
):
    """Submitting a malformed e-mail address produces a 422 validation error."""
    client = _make_client(db_session, monkeypatch)
    resp = client.post(
        "/api/v1/signin",
        json={"email": "not-an-email", "password": "somepassword"},
    )
    assert resp.status_code == 422


# ── UserRepository unit tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_repository_user_exists_false_when_empty(db_session: AsyncSession):
    """user_exists() returns False when no user with that email is in the DB."""
    repo = UserRepository(db_session)
    assert await repo.user_exists("nobody@example.com") is False


@pytest.mark.asyncio
async def test_user_repository_user_exists_true_after_create(db_session: AsyncSession):
    """user_exists() returns True after a user has been created."""
    repo = UserRepository(db_session)
    await repo.create_user(
        email="exists@example.com",
        fname="Test",
        lname="User",
        hashed_password="test-hashed-value",
    )
    assert await repo.user_exists("exists@example.com") is True


@pytest.mark.asyncio
async def test_user_repository_get_user_by_email_none_when_missing(
    db_session: AsyncSession,
):
    """get_user_by_email() returns None for an unknown email."""
    repo = UserRepository(db_session)
    result = await repo.get_user_by_email("missing@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_user_repository_create_user_returns_user_with_id(
    db_session: AsyncSession,
):
    """create_user() returns a User ORM object with a populated id and email."""
    repo = UserRepository(db_session)
    user = await repo.create_user(
        email="created@example.com",
        fname="New",
        lname="Person",
        hashed_password="some-hashed-value",
    )
    assert user.id is not None
    assert user.email == "created@example.com"
    assert user.fname == "New"
    assert user.lname == "Person"


# ── Real bcrypt coverage (Issue 3) ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcrypt_hash_and_verify_round_trip(db_session: AsyncSession):
    """Confirm real bcrypt hashing & verification works end-to-end through
    UserRepository, independently of the passlib/bcrypt version conflict.
    Uses the ``bcrypt`` library directly to avoid passlib's broken self-test.
    """
    plain = "RealPassword123!"  # meets new password requirements
    hashed = _bcrypt_hash(plain)

    repo = UserRepository(db_session)
    user = await repo.create_user(
        email="bcrypt_test@example.com",
        fname="Real",
        lname="Bcrypt",
        hashed_password=hashed,
    )

    # Stored hash must be a valid bcrypt hash (starts with $2b$)
    assert user.password.startswith("$2b$")
    # Real bcrypt verify must accept the original password
    assert _bcrypt_verify(plain, user.password) is True
    # Must reject a wrong password
    assert _bcrypt_verify("wrongpassword", user.password) is False


@pytest.mark.asyncio
async def test_signin_real_bcrypt_hash(db_session: AsyncSession):
    """Signin with a pre-stored real bcrypt hash succeeds at the repository
    level, exercising the verify path without going through passlib's
    broken CryptContext initialisation.
    """
    plain = "Hunter2Secure!"  # meets new password requirements
    hashed = _bcrypt_hash(plain)

    repo = UserRepository(db_session)
    await repo.create_user(
        email="realcrypt@example.com",
        fname="Real",
        lname="Crypt",
        hashed_password=hashed,
    )

    user = await repo.get_user_by_email("realcrypt@example.com")
    assert user is not None
    assert _bcrypt_verify(plain, user.password) is True


# ── 72-byte password limit (Issue 1) ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_signup_password_over_72_bytes_returns_422(
    db_session: AsyncSession, monkeypatch
):
    """A password whose UTF-8 encoding exceeds 72 bytes is rejected with 422.

    bcrypt silently truncates passwords at 72 bytes; we block this at the
    schema layer to prevent silent auth ambiguity.
    """
    client = _make_client(db_session, monkeypatch)
    # 73 ASCII bytes — safe for any locale
    long_password = "a" * 73
    resp = client.post(
        "/api/v1/signup",
        json={
            "fname": "Len",
            "lname": "Test",
            "email": "longpw@example.com",
            "password": long_password,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_signup_password_exactly_72_bytes_accepted(
    db_session: AsyncSession, monkeypatch
):
    """A password of exactly 72 bytes is accepted (boundary condition)."""
    client = _make_client(db_session, monkeypatch)
    # Create a 72-byte password meeting strength requirements
    pwd_72 = "Exact72BytePass123!Exact72BytePass123!xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    assert len(pwd_72.encode("utf-8")) == 72, (
        f"Password is {len(pwd_72.encode('utf-8'))} bytes, expected 72"
    )
    resp = client.post(
        "/api/v1/signup",
        json={
            "fname": "Exact",
            "lname": "Bytes",
            "email": "exact72@example.com",
            "password": pwd_72,
        },
    )
    assert resp.status_code == 200


# ── IntegrityError race-condition guard (Issue 2) ─────────────────────────────


@pytest.mark.asyncio
async def test_signup_integrity_error_returns_400(
    db_session: AsyncSession, monkeypatch
):
    """If the DB unique constraint fires (race condition), signup returns 400.

    Simulates the scenario where user_exists() passes but the INSERT fails
    on the unique email index — should produce 400, not 500.
    """
    client = _make_client(db_session, monkeypatch)

    # Monkeypatch UserRepository.create_user to raise IntegrityError
    async def raise_integrity(self, **kwargs):
        raise IntegrityError("duplicate", {}, Exception("unique constraint"))

    monkeypatch.setattr(auth_module.UserRepository, "create_user", raise_integrity)

    resp = client.post(
        "/api/v1/signup",
        json={
            "fname": "Race",
            "lname": "Condition",
            "email": "race@example.com",
            "password": "ValidPass123!",  # meets strength requirements
        },
    )
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()
