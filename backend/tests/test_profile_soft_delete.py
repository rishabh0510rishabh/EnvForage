"""
Tests for profile soft-delete cascade behaviour.
No database required — service layer is mocked.
Auth dependencies are stubbed out so these tests focus solely on
soft-delete logic and HTTP response mapping.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import require_admin
from app.main import app
from app.models.profile import EnvironmentProfile, ProfilePackage

client = TestClient(app)


def _stub_require_admin() -> None:
    """No-op stub that bypasses admin key validation."""
    return None


@pytest.fixture(autouse=True)
def _override_require_admin():
    """Stub out require_admin for every test in this module."""
    app.dependency_overrides[require_admin] = _stub_require_admin
    yield
    app.dependency_overrides.pop(require_admin, None)


def make_package(profile_id: uuid.UUID) -> ProfilePackage:
    pkg = MagicMock(spec=ProfilePackage)
    pkg.id = uuid.uuid4()
    pkg.profile_id = profile_id
    pkg.deleted_at = None
    return pkg


def make_profile(slug: str = "test-profile") -> EnvironmentProfile:
    profile = MagicMock(spec=EnvironmentProfile)
    profile.id = uuid.uuid4()
    profile.slug = slug
    profile.status = "ACTIVE"
    profile.deleted_at = None
    profile.packages = [make_package(profile.id) for _ in range(3)]
    return profile


# ── 1. Delete non-existent profile returns 404 ───────────────────────────────


def test_delete_profile_not_found_returns_404():
    with patch(
        "app.services.profile_service.delete_profile",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = client.delete("/api/v1/profiles/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["error"]["code"] == "PROFILE_NOT_FOUND"
    assert "does-not-exist" in body["detail"]["error"]["message"]
    assert "details" in body["detail"]["error"]


# ── 2. Successful delete returns 204 ─────────────────────────────────────────


def test_delete_profile_success_returns_204():
    with patch(
        "app.services.profile_service.delete_profile",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = client.delete("/api/v1/profiles/test-profile")

    assert response.status_code == 204


# ── 3. Packages are soft-deleted when profile is deleted ─────────────────────


def test_delete_profile_cascades_deleted_at_to_packages():

    profile = make_profile()

    async def fake_delete(db, slug):
        profile.deleted_at = "2026-01-01T00:00:00Z"
        profile.status = "DELETED"
        for pkg in profile.packages:
            pkg.deleted_at = "2026-01-01T00:00:00Z"
        return True

    with patch("app.services.profile_service.delete_profile", side_effect=fake_delete):
        client.delete(f"/api/v1/profiles/{profile.slug}")

    assert profile.status == "DELETED"
    assert profile.deleted_at is not None
    for pkg in profile.packages:
        assert pkg.deleted_at is not None


# ── 4. No packages remain active after profile deletion ──────────────────────


def test_delete_profile_no_active_packages_remain():
    profile = make_profile()

    async def fake_delete(db, slug):
        for pkg in profile.packages:
            pkg.deleted_at = "2026-01-01T00:00:00Z"
        return True

    with patch("app.services.profile_service.delete_profile", side_effect=fake_delete):
        client.delete(f"/api/v1/profiles/{profile.slug}")

    active = [p for p in profile.packages if p.deleted_at is None]
    assert len(active) == 0


# ── 5. All error responses have consistent format ────────────────────────────


def test_delete_profile_error_has_consistent_format():
    with patch(
        "app.services.profile_service.delete_profile",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = client.delete("/api/v1/profiles/anything")

    error = response.json()["detail"]["error"]
    assert "code" in error
    assert "message" in error
    assert "details" in error


# ── 6. DB error during delete returns 500 ────────────────────────────────────


def test_delete_profile_db_error_returns_500():
    client_no_raise = TestClient(app, raise_server_exceptions=False)
    with patch(
        "app.services.profile_service.delete_profile",
        new_callable=AsyncMock,
        side_effect=Exception("DB error"),
    ):
        response = client_no_raise.delete("/api/v1/profiles/test-profile")

    assert response.status_code == 500
