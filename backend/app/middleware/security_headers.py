"""Security headers middleware.

Adds defense-in-depth HTTP headers to every response:
  - Content-Security-Policy (with violation reporting)
  - X-Frame-Options
  - X-Content-Type-Options
  - Referrer-Policy
  - Strict-Transport-Security (production only)
  - Permissions-Policy
  - Cross-Origin-Opener-Policy
  - X-DNS-Prefetch-Control
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings

# CSP directives — tuned for a Next.js frontend + API backend.
# 'unsafe-inline' for style-src is required because Next.js injects
# inline style tags for CSS Modules.  script-src omits 'unsafe-eval'
# because Next.js production builds do NOT require it.
_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "report-uri /api/v1/csp-report"
)

# Headers applied unconditionally
_COMMON_HEADERS: dict[str, str] = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "X-DNS-Prefetch-Control": "off",
    "Content-Security-Policy": _CSP,
}

# HSTS header only for production (must not be set during local dev)
_HSTS_HEADER = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects security headers into every HTTP response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # Skip Content-Security-Policy for API documentation endpoints to allow Swagger/ReDoc CDN assets
        is_docs_path = request.url.path in ("/api/docs", "/api/redoc", "/api/openapi.json")

        for header, value in _COMMON_HEADERS.items():
            if header == "Content-Security-Policy" and is_docs_path:
                continue
            response.headers.setdefault(header, value)

        if get_settings().environment == "production":
            response.headers.setdefault("Strict-Transport-Security", _HSTS_HEADER)

        return response

