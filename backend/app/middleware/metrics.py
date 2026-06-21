"""Prometheus metrics for API observability.

Exposes:
  - ``/metrics`` endpoint for Prometheus scraping
  - Request count, latency, and status-code histograms
  - AI provider token consumption counters
"""

import time

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.routing import Match

# ── HTTP Metrics ──────────────────────────────────────────────────────────────

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests processed",
    ["method", "route", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

# ── AI Provider Metrics ───────────────────────────────────────────────────────

AI_TOKENS_TOTAL = Counter(
    "ai_tokens_total",
    "Total AI tokens consumed",
    ["provider", "model", "type"],
)

AI_REQUESTS_TOTAL = Counter(
    "ai_requests_total",
    "Total AI provider requests",
    ["provider", "model", "status"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records HTTP request metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        method = request.method
        route = self._get_route(request)

        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        status = str(response.status_code)
        HTTP_REQUESTS_TOTAL.labels(method=method, route=route, status=status).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method, route=route, status=status
        ).observe(duration)

        return response

    def _get_route(self, request: Request) -> str:
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                if hasattr(route, "path"):
                    return str(route.path)
        return request.url.path


def record_ai_token_usage(
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    success: bool = True,
) -> None:
    """Record AI provider token consumption."""
    status = "success" if success else "failure"
    AI_REQUESTS_TOTAL.labels(provider=provider, model=model, status=status).inc()

    if prompt_tokens:
        AI_TOKENS_TOTAL.labels(provider=provider, model=model, type="prompt").inc(
            prompt_tokens
        )
    if completion_tokens:
        AI_TOKENS_TOTAL.labels(provider=provider, model=model, type="completion").inc(
            completion_tokens
        )


def setup_metrics(app: FastAPI) -> None:
    """Attach metrics middleware and /metrics endpoint to the FastAPI app."""
    app.add_middleware(MetricsMiddleware)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )
