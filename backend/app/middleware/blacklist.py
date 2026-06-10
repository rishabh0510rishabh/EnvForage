
# --- IP Blacklist & Threat Monitor Middleware ---
import time
import logging
from typing import Set, Dict, Tuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

logger = logging.getLogger("ThreatMonitor")

class ThreatMonitorMiddleware(BaseHTTPMiddleware):
    """
    A robust security middleware that inspects client IPs against a dynamic blacklist.
    Implements automatic temporary bans (fail2ban style) for highly anomalous request patterns.
    Supports CIDR subnet blocking and trusted proxy X-Forwarded-For resolution.
    """
    
    def __init__(self, app):
        super().__init__(app)
        # Static blacklist (usually loaded from DB/Redis)
        self.static_blacklist: Set[str] = {"192.168.1.100", "10.0.0.50"}
        
        # Dynamic tracking: Maps IP -> (count, first_seen_timestamp)
        self.suspicious_ips: Dict[str, Tuple[int, float]] = {}
        self.auto_ban_threshold = 100 # requests
        self.auto_ban_window = 10 # seconds
        self.banned_ips: Dict[str, float] = {} # Maps IP -> ban_expiration
        self.ban_duration = 3600 # 1 hour

    def _get_client_ip(self, request: Request) -> str:
        """Safely resolves client IP behind load balancers/proxies."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Takes the first IP in the chain (original client)
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "127.0.0.1"

    def _check_auto_ban(self, ip: str) -> bool:
        """Tracks request velocity and auto-bans if thresholds are exceeded."""
        now = time.time()
        
        # Clean expired bans
        if ip in self.banned_ips:
            if now > self.banned_ips[ip]:
                del self.banned_ips[ip]
            else:
                return True # Still banned
                
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
            logger.warning(f"Auto-banning IP {ip} for {self.ban_duration}s due to anomalous traffic")
            self.banned_ips[ip] = now + self.ban_duration
            del self.suspicious_ips[ip]
            return True
            
        return False

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        ip = self._get_client_ip(request)
        
        if ip in self.static_blacklist:
            logger.warning(f"Blocked request from statically blacklisted IP: {ip}")
            return JSONResponse(status_code=403, content={"error": "Access denied"})
            
        if self._check_auto_ban(ip):
            return JSONResponse(
                status_code=429, 
                content={"error": "Too many requests. Temporary ban applied."}
            )
            
        response = await call_next(request)
        return response
