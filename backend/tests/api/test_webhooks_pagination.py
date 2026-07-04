"""
Tests for GET /api/v1/webhooks pagination.
Issue #1056 - list endpoints did not implement pagination, risking
memory issues at scale.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import require_admin
from app.config import get_settings
from app.main import app
from app.models.webhook import Webhook

BASE = "/api/v1/webhooks"
_settings = get_settings()


@pytest.fixture
def client():
    """Fixture that yields a TestClient with lifespan events properly handled."""
    with TestClient(app) as c:
        yield c


def _stub_require_admin() -> None:
    """No-op stub that bypasses admin key validation."""
    return None


@pytest.fixture(autouse=True)
def _override_require_admin():
    """Stub out require_admin for every test in this module."""
    app.dependency_overrides[require_admin] = _stub_require_admin
    yield
    app.dependency_overrides.pop(require_admin, None)


def make_webhook(target_url: str = "https://example.com/hook") -> Webhook:
    return Webhook(
        id=uuid.uuid4(),
        target_url=target_url,
        secret="s3cr3t",
        events=["diagnose.completed"],
        is_active=True,
        created_at=datetime.now(UTC),
    )


def test_list_webhooks_returns_paginated_shape(client):
    webhooks = [make_webhook(f"https://example.com/hook{i}") for i in range(3)]
    with patch(
        "app.api.v1.webhooks.list_webhooks_paginated",
        new_callable=AsyncMock,
        return_value=(webhooks, 3),
    ):
        res = client.get(BASE)

    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == _settings.default_page_size
    assert len(body["webhooks"]) == 3


def test_list_webhooks_respects_custom_page_and_limit(client):
    webhooks = [make_webhook()]
    with patch(
        "app.api.v1.webhooks.list_webhooks_paginated",
        new_callable=AsyncMock,
        return_value=(webhooks, 50),
    ) as mock_list:
        res = client.get(BASE, params={"page": 3, "limit": 10})

    assert res.status_code == 200
    body = res.json()
    assert body["page"] == 3
    assert body["page_size"] == 10
    assert body["total"] == 50
    mock_list.assert_awaited_once()
    _, called_page, called_limit = mock_list.call_args[0]
    assert called_page == 3
    assert called_limit == 10


def test_list_webhooks_empty_result(client):
    with patch(
        "app.api.v1.webhooks.list_webhooks_paginated",
        new_callable=AsyncMock,
        return_value=([], 0),
    ):
        res = client.get(BASE)

    assert res.status_code == 200
    body = res.json()
    assert body["webhooks"] == []
    assert body["total"] == 0


def test_list_webhooks_rejects_limit_over_max(client):
    res = client.get(BASE, params={"limit": _settings.max_page_size + 1})
    assert res.status_code == 422


def test_list_webhooks_rejects_page_below_1(client):
    res = client.get(BASE, params={"page": 0})
    assert res.status_code == 422


def test_list_webhooks_default_page_and_limit(client):
    with patch(
        "app.api.v1.webhooks.list_webhooks_paginated",
        new_callable=AsyncMock,
        return_value=([], 0),
    ) as mock_list:
        client.get(BASE)

    mock_list.assert_awaited_once()
    _, called_page, called_limit = mock_list.call_args[0]
    assert called_page == 1
    assert called_limit == _settings.default_page_size
