"""
Tests for centralized exception handling.
No database required — service layer is mocked.
"""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_profile_not_found_returns_404():
    with patch(
        "app.services.profile_service.get_profile_by_slug",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = client.get("/api/v1/profiles/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["error"]["code"] == "PROFILE_NOT_FOUND"
    assert "does-not-exist" in body["detail"]["error"]["message"]
    assert "details" in body["detail"]["error"]


def test_create_duplicate_profile_returns_409():
    from sqlalchemy.exc import IntegrityError

    with patch(
        "app.services.profile_service.create_profile",
        new_callable=AsyncMock,
        side_effect=IntegrityError("duplicate", {}, None),
    ):
        response = client.post(
            "/api/v1/profiles",
            json={
                "slug": "test-profile",
                "name": "Test",
                "description": "desc",
                "os_support": ["LINUX"],
                "python_versions": ["3.11"],
                "packages": [],
            },
        )

    assert response.status_code == 409
    body = response.json()
    assert body["detail"]["error"]["code"] == "CONFLICT_ERROR"


def test_invalid_request_body_returns_422():
    response = client.post("/api/v1/profiles", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["detail"]["error"]["code"] == "VALIDATION_ERROR"
    assert body["detail"]["error"]["message"] == "Request validation failed."
    for error in body["detail"]["error"]["details"]:
        assert "input" not in error


def test_all_errors_have_consistent_format():
    with patch(
        "app.services.profile_service.get_profile_by_slug",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = client.get("/api/v1/profiles/anything")

    error = response.json()["detail"]["error"]
    assert "code" in error
    assert "message" in error
    assert "details" in error
