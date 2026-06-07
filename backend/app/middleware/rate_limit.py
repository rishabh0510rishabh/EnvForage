"""In-memory rate limiter for AI endpoints.

Implements a sliding-window rate limiter with two backends:
  - ``InMemoryBackend``: default, suitable for single-instance / development.
  - ``RedisBackend``: used in production when ``REDIS_URL`` is set. Correct
    across multiple uvicorn workers because state lives in Redis, not in-process.

Design:
    - Rate limits are per-client-IP
    - X-Forwarded-For is only trusted when the direct peer is a known private proxy
    - AI endpoints get stricter limits than general API endpoints
    - Returns standard HTTP 429 with Retry-After header
    - Configurable via Settings (rate_limit_ai_rpm, rate_limit_general_rpm)

Usage::

    from app.middleware.rate_limit import RateLimiter, ai_rate_limit

    # As a FastAPI dependency
    @router.post("/troubleshoot")
    async def troubleshoot(
        request: TroubleshootRequest,
        _rate_limit: None = Depends(ai_rate_limit),
    ):
        ...
"""

import ipaddress
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any

from fastapi import HTTPException, Request
from redis.exceptions import ConnectionError as RedisConnError
from redis.exceptions import TimeoutError as RedisTimeout

from app.config import get_settings

# Private and loopback CIDRs that may legitimately set X-Forwarded-For.
# Only peers whose address falls within these ranges are considered trusted
# proxies; all other peers must be rate-limited by their direct IP.
_TRUSTED_PROXY_CIDRS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
)

logger = logging.getLogger(__name__)


# ── Backend ABC ───────────────────────────────────────────────────────────────


class RateLimitBackend(ABC):
    """Abstract rate limit storage backend."""

    @abstractmethod
    async def is_allowed(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, dict[str, Any]]:
        """
        Check if a request is allowed under the rate limit.

        Args:
            key: Unique identifier (e.g. IP address).
            max_requests: Maximum requests allowed in the window.
            window_seconds: Time window in seconds.

        Returns:
            Tuple of (allowed: bool, info: dict with remaining, reset, limit).
        """
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        """Remove expired entries. Called periodically."""
        ...


# ── In-memory backend (development / single-worker) ───────────────────────────


class InMemoryBackend(RateLimitBackend):
    """
    Sliding-window rate limiter using in-memory storage.

    Thread-safe for async (single process). For multi-worker deployments,
    use RedisBackend instead.
    """

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 60.0  # seconds

    async def is_allowed(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, dict[str, Any]]:
        now = time.monotonic()

        if now - self._last_cleanup > self._cleanup_interval:
            await self.cleanup()
            self._last_cleanup = now

        window_start = now - window_seconds
        self._requests[key] = [ts for ts in self._requests[key] if ts > window_start]

        current_count = len(self._requests[key])
        remaining = max(0, max_requests - current_count - 1)

        if current_count >= max_requests:
            earliest = min(self._requests[key]) if self._requests[key] else now
            retry_after = int(earliest + window_seconds - now) + 1
            return False, {
                "remaining": 0,
                "limit": max_requests,
                "reset": retry_after,
                "window": window_seconds,
            }

        self._requests[key].append(now)
        return True, {
            "remaining": remaining,
            "limit": max_requests,
            "reset": window_seconds,
            "window": window_seconds,
        }

    async def cleanup(self) -> None:
        now = time.monotonic()
        empty_keys = [
            key
            for key, timestamps in list(self._requests.items())
            if not timestamps or max(timestamps) < now - 300
        ]
        for key in empty_keys:
            del self._requests[key]
        if empty_keys:
            logger.debug("Rate limiter cleanup: removed %d stale keys", len(empty_keys))


# ── Redis backend (production / multi-worker) ─────────────────────────────────


class RedisBackend(RateLimitBackend):
    """
    Sliding-window rate limiter backed by Redis.

    Uses a sorted set per key: members are unique request IDs, scores are
    timestamps. This gives exact sliding-window counts without a Lua script.

    Requires: redis[asyncio] — listed in pyproject.toml dependencies.
    """

    def __init__(self, redis_url: str) -> None:
        try:
            import redis.asyncio as aioredis
        except ImportError as exc:
            raise RuntimeError(
                "redis[asyncio] is not installed but REDIS_URL is set. "
                "Add 'redis[asyncio]' to backend/pyproject.toml dependencies "
                "and reinstall: pip install -e ."
            ) from exc
        self._client = aioredis.from_url(redis_url, decode_responses=True)

    async def is_allowed(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, dict[str, Any]]:
        import uuid

        now = time.time()
        window_start = now - window_seconds

        pipe = self._client.pipeline()
        # Remove timestamps outside the current window
        pipe.zremrangebyscore(key, "-inf", window_start)
        # Count remaining in window
        pipe.zcard(key)
        # Add current request (scored by timestamp, unique member)
        member = f"{now}:{uuid.uuid4().hex}"
        pipe.zadd(key, {member: now})
        # Expire the key after the window so Redis cleans up automatically
        pipe.expire(key, window_seconds + 1)
        results = await pipe.execute()

        current_count = results[1]  # count BEFORE this request was added

        if current_count >= max_requests:
            # Roll back the zadd — request is rejected
            await self._client.zrem(key, member)
            # Find when the oldest request in the window expires
            oldest = await self._client.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(float(oldest[0][1]) + window_seconds - now) + 1
            else:
                retry_after = int(window_seconds)
            return False, {
                "remaining": 0,
                "limit": max_requests,
                "reset": retry_after,
                "window": window_seconds,
            }

        remaining = max(0, max_requests - current_count - 1)
        return True, {
            "remaining": remaining,
            "limit": max_requests,
            "reset": int(window_seconds),
            "window": window_seconds,
        }

    async def cleanup(self) -> None:
        # Redis TTLs handle cleanup automatically via the expire() call above
        pass


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mask_redis_url(url: str) -> str:
    """
    Mask the password in a Redis URL for safe logging.

        redis://:password@host:port/db      →  redis://:***@host:port/db
        redis://user:password@host:port/db  →  redis://user:***@host:port/db
        redis://host:port/db                →  redis://host:port/db  (unchanged)
    """
    if "@" not in url:
        return url
    scheme_and_creds, hostpart = url.rsplit("@", 1)
    creds = scheme_and_creds.split("//", 1)[-1]
    if ":" in creds:
        # Mask everything after the last colon in the credentials segment
        prefix = scheme_and_creds.rsplit(":", 1)[0]
        return f"{prefix}:***@{hostpart}"
    return url


# ── Backend factory ───────────────────────────────────────────────────────────


def _make_backend() -> RateLimitBackend:
    """
    Return a RedisBackend if REDIS_URL is configured, else InMemoryBackend.
    Called once at import time — settings are already loaded by then.
    """
    settings = get_settings()
    if settings.redis_url:
        logger.info(
            "Rate limiter using Redis backend: %s", _mask_redis_url(settings.redis_url)
        )
        return RedisBackend(settings.redis_url)
    logger.info("Rate limiter using in-memory backend (single-instance only)")
    return InMemoryBackend()


_backend = _make_backend()

# Fallback used when RedisBackend raises a connection error at request time.
# A single shared instance preserves the sliding-window state across all
# requests that arrive while Redis is degraded.
_fallback_backend = InMemoryBackend()


# ── Rate Limiter ──────────────────────────────────────────────────────────────


class RateLimiter:
    """
    Configurable rate limiter for FastAPI dependency injection.

    Usage::

        limiter = RateLimiter(max_requests=10, window_seconds=60)

        @router.post("/endpoint")
        async def endpoint(_: None = Depends(limiter)):
            ...
    """

    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: int = 60,
        backend: RateLimitBackend | None = None,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.backend = backend or _backend

    async def __call__(self, request: Request) -> None:
        """FastAPI dependency — raises HTTPException(429) if rate limited."""
        client_ip = self._get_client_ip(request)
        key = f"rate_limit:{request.url.path}:{client_ip}"

        try:
            allowed, info = await self.backend.is_allowed(
                key, self.max_requests, self.window_seconds,
            )
        except Exception as exc:
            if isinstance(exc, (RedisConnError, RedisTimeout)):
                logger.warning(
                    "Redis connection error during rate limit check for %s on %s "
                    "— falling back to in-memory backend. Error: %s",
                    client_ip, request.url.path, exc,
                )
                allowed, info = await _fallback_backend.is_allowed(
                    key, self.max_requests, self.window_seconds,
                )
            else:
                # Non-Redis exception (programming bug, etc.) — re-raise so it
                # is not silently swallowed.
                raise

        if not allowed:
            logger.warning(
                "Rate limit exceeded: %s on %s (limit: %d/%ds)",
                client_ip,
                request.url.path,
                self.max_requests,
                self.window_seconds,
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": (
                        f"Too many requests. Limit: {self.max_requests} per "
                        f"{self.window_seconds}s. Try again in {info['reset']}s."
                    ),
                    "retry_after": info["reset"],
                },
                headers={"Retry-After": str(info["reset"])},
            )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, trusting X-Forwarded-For only from known proxy peers."""
        peer = request.client.host if request.client else None
        if peer:
            try:
                peer_addr = ipaddress.ip_address(peer)
                if any(peer_addr in cidr for cidr in _TRUSTED_PROXY_CIDRS):
                    forwarded = request.headers.get("x-forwarded-for")
                    if forwarded:
                        return forwarded.split(",")[0].strip()
            except ValueError:
                pass
        return peer or "unknown"


# ── Pre-configured limiters ───────────────────────────────────────────────────

# AI endpoints: 10 requests per minute (LLM calls are expensive)
ai_rate_limit = RateLimiter(max_requests=10, window_seconds=60)

# Repair endpoints: 20 requests per minute (template rendering is cheap)
repair_rate_limit = RateLimiter(max_requests=20, window_seconds=60)

# General API: 60 requests per minute
general_rate_limit = RateLimiter(max_requests=60, window_seconds=60)

# Auth endpoints (/signup, /signin).
# Reads max_requests from settings.rate_limit_auth_rpm (default 20 rpm) so
# operators can tune the limit without a code change.  Uses a separate
# limiter instance so auth traffic never competes with general-API quota.
_auth_settings = get_settings()
auth_rate_limit = RateLimiter(
    max_requests=_auth_settings.rate_limit_auth_rpm,
    window_seconds=60,
)
