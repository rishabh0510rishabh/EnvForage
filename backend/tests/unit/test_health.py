"""Tests for the /health endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import create_app

# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_db_ok():
    """Returns a mock AsyncSessionLocal context manager that succeeds."""
    session = AsyncMock()
    session.execute = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _mock_redis_ok():
    """Returns a mock Redis client that responds to ping."""
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    return redis


# ── All healthy ───────────────────────────────────────────────────────────────


def test_health_all_ok():
    with (
        patch("app.main.AsyncSessionLocal", return_value=_mock_db_ok()),
        patch(
            "app.main.get_redis_client", new=AsyncMock(return_value=_mock_redis_ok())
        ),
    ):
        response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["services"]["database"] == "ok"
    assert body["services"]["redis"] == "ok"
    assert "version" in body


# ── Database down ─────────────────────────────────────────────────────────────


def test_health_db_unavailable():
    bad_cm = MagicMock()
    bad_cm.__aenter__ = AsyncMock(side_effect=Exception("db connection refused"))
    bad_cm.__aexit__ = AsyncMock(return_value=False)
    with (
        patch("app.main.AsyncSessionLocal", return_value=bad_cm),
        patch(
            "app.main.get_redis_client", new=AsyncMock(return_value=_mock_redis_ok())
        ),
    ):
        response = TestClient(create_app()).get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"]["database"] == "unavailable"
    assert body["services"]["redis"] == "ok"


# ── Redis down ────────────────────────────────────────────────────────────────


def test_health_redis_unavailable():
    dead_redis = AsyncMock()
    dead_redis.ping = AsyncMock(side_effect=Exception("redis connection refused"))
    with (
        patch("app.main.AsyncSessionLocal", return_value=_mock_db_ok()),
        patch("app.main.get_redis_client", new=AsyncMock(return_value=dead_redis)),
    ):
        response = TestClient(create_app()).get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"]["database"] == "ok"
    assert body["services"]["redis"] == "unavailable"


# ── Both down ─────────────────────────────────────────────────────────────────


def test_health_both_unavailable():
    bad_cm = MagicMock()
    bad_cm.__aenter__ = AsyncMock(side_effect=Exception("db down"))
    bad_cm.__aexit__ = AsyncMock(return_value=False)
    dead_redis = AsyncMock()
    dead_redis.ping = AsyncMock(side_effect=Exception("redis down"))
    with (
        patch("app.main.AsyncSessionLocal", return_value=bad_cm),
        patch("app.main.get_redis_client", new=AsyncMock(return_value=dead_redis)),
    ):
        response = TestClient(create_app()).get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"]["database"] == "unavailable"
    assert body["services"]["redis"] == "unavailable"


# ── Redis not configured ──────────────────────────────────────────────────────


def test_health_redis_not_configured():
    with (
        patch("app.main.AsyncSessionLocal", return_value=_mock_db_ok()),
        patch("app.main.get_redis_client", new=AsyncMock(return_value=None)),
    ):
        response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["services"]["redis"] == "not_configured"


# ── Redis timeout (TCP blackhole) ─────────────────────────────────────────────


def test_health_redis_timeout():
    """Verify that a Redis ping timeout causes degraded status within 1s."""
    timed_out_redis = AsyncMock()
    timed_out_redis.ping = AsyncMock(side_effect=TimeoutError())
    with (
        patch("app.main.AsyncSessionLocal", return_value=_mock_db_ok()),
        patch(
            "app.main.get_redis_client", new=AsyncMock(return_value=timed_out_redis)
        ),
    ):
        response = TestClient(create_app()).get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"]["database"] == "ok"
    assert body["services"]["redis"] == "unavailable"
