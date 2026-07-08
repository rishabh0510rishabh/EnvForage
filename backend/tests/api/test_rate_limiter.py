"""
Integration tests for the rate limiting middleware.

Tests exercise RateLimiter and its two backends (InMemoryBackend,
RedisBackend) directly, since the middleware's logic is fully unit-testable
in isolation from the HTTP/auth layer above it. This avoids needing JWT
auth fixtures while still covering: sliding-window enforcement, per-key
isolation, trusted-proxy IP resolution, and Redis-failure fallback.
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from redis.exceptions import ConnectionError as RedisConnError
from redis.exceptions import TimeoutError as RedisTimeout

from app.middleware.rate_limit import (
    InMemoryBackend,
    RateLimiter,
    RedisBackend,
    _mask_redis_url,
)


def make_request(
    client_host: str | None = "203.0.113.5",
    headers: dict[str, str] | None = None,
    path: str = "/api/v1/test",
) -> Request:
    """Build a minimal Request for testing _get_client_ip and __call__."""
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": raw_headers,
        "client": (client_host, 12345) if client_host else None,
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
    }
    return Request(scope)


# ── InMemoryBackend ──────────────────────────────────────────────────────


class TestInMemoryBackend:
    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self):
        backend = InMemoryBackend()
        info = {}
        for _ in range(3):
            allowed, info = await backend.is_allowed("key1", max_requests=5, window_seconds=60)
            assert allowed is True
        assert info["remaining"] == 2

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self):
        backend = InMemoryBackend()
        for _ in range(3):
            await backend.is_allowed("key2", max_requests=3, window_seconds=60)
        allowed, info = await backend.is_allowed("key2", max_requests=3, window_seconds=60)
        assert allowed is False
        assert info["remaining"] == 0
        assert info["limit"] == 3
        assert info["reset"] > 0

    @pytest.mark.asyncio
    async def test_keys_are_isolated(self):
        backend = InMemoryBackend()
        for _ in range(3):
            await backend.is_allowed("client-a", max_requests=3, window_seconds=60)
        allowed_a, _ = await backend.is_allowed("client-a", max_requests=3, window_seconds=60)
        allowed_b, _ = await backend.is_allowed("client-b", max_requests=3, window_seconds=60)
        assert allowed_a is False
        assert allowed_b is True

    @pytest.mark.asyncio
    async def test_sliding_window_expiry(self, monkeypatch):
        backend = InMemoryBackend()
        fake_now = [1000.0]
        monkeypatch.setattr(time, "monotonic", lambda: fake_now[0])

        for _ in range(2):
            await backend.is_allowed("key3", max_requests=2, window_seconds=10)
        allowed, _ = await backend.is_allowed("key3", max_requests=2, window_seconds=10)
        assert allowed is False

        fake_now[0] += 11
        allowed, info = await backend.is_allowed("key3", max_requests=2, window_seconds=10)
        assert allowed is True
        assert info["remaining"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_removes_stale_keys(self, monkeypatch):
        backend = InMemoryBackend()
        fake_now = [0.0]
        monkeypatch.setattr(time, "monotonic", lambda: fake_now[0])

        await backend.is_allowed("stale-key", max_requests=5, window_seconds=60)
        assert "stale-key" in backend._requests

        fake_now[0] += 400
        await backend.cleanup()
        assert "stale-key" not in backend._requests


# ── RedisBackend ──────────────────────────────────────────────────────────


class TestRedisBackend:
    def _make_backend_with_mock_client(self):
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_client = MagicMock()
            mock_pipe = MagicMock()
            mock_client.pipeline.return_value = mock_pipe
            mock_from_url.return_value = mock_client
            backend = RedisBackend("redis://localhost:6379/0")
            return backend, mock_client, mock_pipe

    @pytest.mark.asyncio
    async def test_allows_when_under_limit(self):
        backend, mock_client, mock_pipe = self._make_backend_with_mock_client()
        mock_pipe.execute = AsyncMock(return_value=[None, 2, None, None])
        mock_client.zrem = AsyncMock()

        allowed, info = await backend.is_allowed("key", max_requests=5, window_seconds=60)
        assert allowed is True
        assert info["remaining"] == 2

    @pytest.mark.asyncio
    async def test_blocks_when_over_limit_and_rolls_back(self):
        backend, mock_client, mock_pipe = self._make_backend_with_mock_client()
        mock_pipe.execute = AsyncMock(return_value=[None, 5, None, None])
        mock_client.zrem = AsyncMock()
        mock_client.zrange = AsyncMock(return_value=[("member", str(time.time() - 10))])

        allowed, info = await backend.is_allowed("key", max_requests=5, window_seconds=60)
        assert allowed is False
        assert info["remaining"] == 0
        mock_client.zrem.assert_awaited_once()

    def test_mask_redis_url_with_password(self):
        assert _mask_redis_url("redis://:secret@host:6379/0") == "redis://:***@host:6379/0"

    def test_mask_redis_url_with_user_and_password(self):
        assert _mask_redis_url("redis://user:secret@host:6379/0") == "redis://user:***@host:6379/0"

    def test_mask_redis_url_without_credentials(self):
        assert _mask_redis_url("redis://host:6379/0") == "redis://host:6379/0"


# ── RateLimiter (dependency) ───────────────────────────────────────────────


class TestRateLimiterDependency:
    @pytest.mark.asyncio
    async def test_allows_request_under_limit(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60, backend=InMemoryBackend())
        await limiter(make_request())

    @pytest.mark.asyncio
    async def test_raises_429_when_limit_exceeded(self):
        backend = InMemoryBackend()
        limiter = RateLimiter(max_requests=2, window_seconds=60, backend=backend)
        request = make_request()

        await limiter(request)
        await limiter(request)

        with pytest.raises(HTTPException) as exc_info:
            await limiter(request)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["error"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in exc_info.value.headers

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("exc", "message"),
        [
            (RedisConnError, "connection refused"),
            (RedisTimeout, "timed out"),
        ],
    )
    async def test_redis_failures_use_in_memory_fallback(self, monkeypatch, exc, message):
        fallback_backend = InMemoryBackend()
        monkeypatch.setattr("app.middleware.rate_limit._fallback_backend", fallback_backend)

        broken_backend = AsyncMock()
        broken_backend.is_allowed.side_effect = exc(message)
        limiter = RateLimiter(max_requests=1, window_seconds=60, backend=broken_backend)
        request = make_request()

        # First request: fallback allows it (quota=1, now exhausted)
        await limiter(request)
        # Second request: fallback blocks it — proving fallback is actually used
        with pytest.raises(HTTPException):
            await limiter(request)

    @pytest.mark.asyncio
    async def test_non_redis_exception_is_reraised(self):
        broken_backend = AsyncMock()
        broken_backend.is_allowed.side_effect = ValueError("unexpected bug")
        limiter = RateLimiter(max_requests=5, window_seconds=60, backend=broken_backend)

        with pytest.raises(ValueError):
            await limiter(make_request())

    @pytest.mark.asyncio
    async def test_different_paths_get_independent_quotas(self):
        backend = InMemoryBackend()
        limiter = RateLimiter(max_requests=1, window_seconds=60, backend=backend)

        req_a = make_request(path="/api/v1/a")
        req_b = make_request(path="/api/v1/b")

        await limiter(req_a)
        await limiter(req_b)

        with pytest.raises(HTTPException):
            await limiter(req_a)

    @pytest.mark.asyncio
    async def test_different_clients_get_independent_quotas(self):
        backend = InMemoryBackend()
        limiter = RateLimiter(max_requests=1, window_seconds=60, backend=backend)

        req_a = make_request(client_host="203.0.113.10")
        req_b = make_request(client_host="203.0.113.20")

        await limiter(req_a)
        await limiter(req_b)

        with pytest.raises(HTTPException):
            await limiter(req_a)


# ── Trusted proxy / client IP resolution ───────────────────────────────────


class TestClientIpResolution:
    def test_trusted_proxy_honors_x_forwarded_for(self):
        limiter = RateLimiter()
        request = make_request(
            client_host="10.0.0.5",
            headers={"x-forwarded-for": "198.51.100.7, 10.0.0.5"},
        )
        assert limiter._get_client_ip(request) == "198.51.100.7"

    def test_untrusted_peer_ignores_x_forwarded_for(self):
        limiter = RateLimiter()
        request = make_request(
            client_host="203.0.113.50",
            headers={"x-forwarded-for": "198.51.100.7"},
        )
        assert limiter._get_client_ip(request) == "203.0.113.50"

    def test_loopback_peer_is_trusted(self):
        limiter = RateLimiter()
        request = make_request(
            client_host="127.0.0.1",
            headers={"x-forwarded-for": "198.51.100.7"},
        )
        assert limiter._get_client_ip(request) == "198.51.100.7"

    def test_no_client_falls_back_to_unknown(self):
        limiter = RateLimiter()
        request = make_request(client_host=None)
        assert limiter._get_client_ip(request) == "unknown"


# ── Pre-configured limiters ────────────────────────────────────────────────


class TestPreconfiguredLimiters:
    def test_ai_rate_limit_is_10_per_minute(self):
        from app.middleware.rate_limit import ai_rate_limit
        assert ai_rate_limit.max_requests == 10
        assert ai_rate_limit.window_seconds == 60

    def test_repair_rate_limit_is_20_per_minute(self):
        from app.middleware.rate_limit import repair_rate_limit
        assert repair_rate_limit.max_requests == 20
        assert repair_rate_limit.window_seconds == 60

    def test_general_rate_limit_is_60_per_minute(self):
        from app.middleware.rate_limit import general_rate_limit
        assert general_rate_limit.max_requests == 60
        assert general_rate_limit.window_seconds == 60

    def test_auth_rate_limit_reads_from_settings(self):
        from app.config import get_settings
        from app.middleware.rate_limit import auth_rate_limit
        settings = get_settings()
        assert auth_rate_limit.max_requests == settings.rate_limit_auth_rpm
        assert auth_rate_limit.window_seconds == 60
