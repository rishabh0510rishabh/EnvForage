
# --- IP Blacklist & Threat Monitor Middleware ---
import asyncio
import ipaddress
import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.middleware.rate_limit import _TRUSTED_PROXY_CIDRS

logger = logging.getLogger("ThreatMonitor")


class ThreatMonitorMiddleware(BaseHTTPMiddleware):
    """
    Security middleware that inspects client IPs against a dynamic blacklist.
    Implements automatic temporary bans (fail2ban style) for anomalous traffic.
    Uses trusted-proxy logic to resolve client IPs behind load balancers.
    """

    def __init__(self, app):
        super().__init__(app)
        # Static blacklist — load from Redis or database at startup.
        # Never hardcode internal IPs (they are often shared/dynamic).
        self.static_blacklist: set[str] = set()

        # Dynamic tracking: Maps IP -> (count, first_seen_timestamp)
        self.suspicious_ips: dict[str, tuple[int, float]] = {}
        self.auto_ban_threshold = 100  # requests
        self.auto_ban_window = 10  # seconds
        self.banned_ips: dict[str, float] = {}  # Maps IP -> ban_expiration
        self.ban_duration = 3600  # 1 hour

        # Lock protects shared mutable state across concurrent requests
        self._lock = asyncio.Lock()

    def _get_client_ip(self, request: Request) -> str:
        """Resolve client IP, only trusting X-Forwarded-For from private proxies."""
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

    async def _check_auto_ban(self, ip: str) -> bool:
        """Track request velocity and auto-ban if thresholds are exceeded."""
        now = time.time()

        async with self._lock:
            # Clean expired bans
            if ip in self.banned_ips:
                if now > self.banned_ips[ip]:
                    del self.banned_ips[ip]
                else:
                    return True  # Still banned

            if ip not in self.suspicious_ips:
                self.suspicious_ips[ip] = (1, now)
                return False

            count, first_seen = self.suspicious_ips[ip]

            # Reset window if expired
            if now - first_seen > self.auto_ban_window:
                self.suspicious_ips[ip] = (1, now)
                return False

            count += 1
            self.suspicious_ips[ip] = (count, first_seen)

            if count > self.auto_ban_threshold:
                logger.warning(
                    "Auto-banning IP %s for %ds due to anomalous traffic",
                    ip, self.ban_duration,
                )
                self.banned_ips[ip] = now + self.ban_duration
                del self.suspicious_ips[ip]
                return True

        return False

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        ip = self._get_client_ip(request)

        if ip in self.static_blacklist:
            logger.warning("Blocked request from statically blacklisted IP: %s", ip)
            return JSONResponse(status_code=403, content={"error": "Access denied"})

        if await self._check_auto_ban(ip):
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests. Temporary ban applied."},
            )

        response = await call_next(request)
        return response
