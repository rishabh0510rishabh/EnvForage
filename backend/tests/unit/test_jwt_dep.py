"""Unit tests for the get_current_user JWT dependency (app.api.deps).

Tests cover:
- Valid token → returns email
- Missing token → 401
- Tampered / invalid token → 401
- Expired token → 401 with TOKEN_EXPIRED error code
- No email field in payload → 401
- /me endpoint integration
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.main import create_app

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_token(payload: dict) -> str:
    settings = get_settings()
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _valid_token(email: str = "test@example.com", hours: int = 1) -> str:
    exp = datetime.now(UTC) + timedelta(hours=hours)
    return _make_token({"email": email, "exp": exp})


def _expired_token(email: str = "expired@example.com") -> str:
    exp = datetime.now(UTC) - timedelta(seconds=1)
    return _make_token({"email": email, "exp": exp})


def _make_test_client(db_session) -> TestClient:
    test_app = create_app()

    async def override_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_db
    return TestClient(test_app, raise_server_exceptions=True)


# ── get_current_user unit tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    """A properly signed, non-expired token returns the email."""
    from fastapi.security import HTTPAuthorizationCredentials

    token = _valid_token("alice@example.com")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    email = await get_current_user(creds)
    assert email == "alice@example.com"


@pytest.mark.asyncio
async def test_get_current_user_no_credentials():
    """No Authorization header → 401."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """A garbage token string → 401."""
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.jwt")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_get_current_user_expired_token():
    """An expired token → 401 with TOKEN_EXPIRED error code."""
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=_expired_token()
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_get_current_user_wrong_secret():
    """Token signed with wrong key → 401."""
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    bad_token = jwt.encode(
        {"email": "hack@evil.com", "exp": datetime.now(UTC) + timedelta(hours=1)},
        "wrong-secret",
        algorithm="HS256",
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=bad_token)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_missing_email_claim():
    """Token with no 'email' field in payload → 401."""
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    token = _make_token({"sub": "someuser", "exp": datetime.now(UTC) + timedelta(hours=1)})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds)
    assert exc_info.value.status_code == 401


# ── /me endpoint integration tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_me_endpoint_with_valid_token(db_session):
    """/me returns the authenticated user's email."""
    client = _make_test_client(db_session)
    token = _valid_token("me@example.com")
    resp = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"email": "me@example.com"}


@pytest.mark.asyncio
async def test_me_endpoint_without_token(db_session):
    """/me without Authorization header → 401."""
    client = _make_test_client(db_session)
    resp = client.get("/api/v1/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint_with_expired_token(db_session):
    """/me with expired token → 401 TOKEN_EXPIRED."""
    client = _make_test_client(db_session)
    token = _expired_token()
    resp = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_me_endpoint_with_tampered_token(db_session):
    """/me with a tampered token → 401."""
    client = _make_test_client(db_session)
    token = _valid_token("victim@example.com") + "tampered"
    resp = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
