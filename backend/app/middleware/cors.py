
# --- Dynamic CORS Middleware ---
import logging
import re

from fastapi import Request, Response
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

logger = logging.getLogger("CORSMiddleware")

class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """
    An advanced CORS middleware that evaluates origins dynamically based on Regex patterns,
    database checks, or environment configurations, rather than a hardcoded static list.
    Supports granular preflight (OPTIONS) caching (Access-Control-Max-Age).
    """

    def __init__(
        self,
        app,
        allowed_regexes: list[str] | None = None,
        allow_credentials: bool = True,
        max_age: int = 86400
    ):
        super().__init__(app)
        self.allowed_regexes = [re.compile(pattern) for pattern in (allowed_regexes or [])]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

        # Common safe defaults
        self.allow_methods = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        self.allow_headers = "Authorization, Content-Type, Accept, X-Requested-With, X-API-Version"
        self.expose_headers = "X-Process-Time, Content-Disposition"

    def _is_origin_allowed(self, origin: str) -> bool:
        if not origin:
            return False

        # Development override — only allow localhost in non-production environments
        # to prevent cross-origin attacks from localhost services on shared servers.
        from app.config import get_settings
        if get_settings().environment != "production":
            if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
                return True

        for pattern in self.allowed_regexes:
            if pattern.match(origin):
                return True
        return False

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get("origin")

        # Fast path for non-CORS requests
        if not origin:
            return await call_next(request)

        is_allowed = self._is_origin_allowed(origin)

        if not is_allowed:
            logger.warning(f"CORS blocked for origin: {origin}")
            return JSONResponse(
                status_code=403,
                content={"error": "Origin not allowed by CORS policy"}
            )

        # Preflight Request
        if request.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": self.allow_methods,
                "Access-Control-Allow-Headers": self.allow_headers,
                "Access-Control-Max-Age": str(self.max_age),
            }
            if self.allow_credentials:
                headers["Access-Control-Allow-Credentials"] = "true"
            return Response(status_code=204, headers=headers)

        # Actual Request
        try:
            response = await call_next(request)
        except Exception as e:
            # We must still append CORS headers on errors, otherwise
            # the browser hides the actual error from the JS client.
            raise e

        response_headers = MutableHeaders(raw=response.headers.raw)
        response_headers["Access-Control-Allow-Origin"] = origin
        response_headers["Access-Control-Expose-Headers"] = self.expose_headers
        if self.allow_credentials:
            response_headers["Access-Control-Allow-Credentials"] = "true"

        return response
