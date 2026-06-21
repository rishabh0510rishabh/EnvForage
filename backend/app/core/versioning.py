
# --- API Versioning Core System ---
from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Request


class VersionedAPIRouter(APIRouter):
    """
    A specialized router that enforces API versioning via headers (Accept-Version)
    or path prefixes, throwing standardized deprecation warnings.
    """
    def __init__(self, current_version: str = "1.0", deprecated_versions: list[str] | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_version = current_version
        self.deprecated_versions = deprecated_versions or []

    def api_route(self, path: str, *args, **kwargs) -> Callable:
        original_route_handler = super().api_route(path, *args, **kwargs)

        def decorator(func: Callable) -> Callable:
            # We wrap the endpoint logic to inject deprecation headers dynamically
            async def wrapped_endpoint(request: Request, *fn_args, **fn_kwargs):
                client_version = request.headers.get("Accept-Version", self.current_version)

                if client_version not in [self.current_version] + self.deprecated_versions:
                    raise HTTPException(status_code=400, detail=f"Unsupported API version: {client_version}")

                response = await func(*fn_args, **fn_kwargs)

                if hasattr(response, "headers"):
                    if client_version in self.deprecated_versions:
                        response.headers["Warning"] = f'299 - "API version {client_version} is deprecated"'
                    response.headers["X-API-Version"] = self.current_version

                return response

            return original_route_handler(wrapped_endpoint)

        return decorator
