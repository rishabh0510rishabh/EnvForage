"""API metrics endpoint — /api/v1/metrics.

Exposes Prometheus-format metrics collected by the prometheus_client library.
The main metrics middleware is registered via setup_metrics() in main.py.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Returns application metrics in Prometheus text exposition format.",
    tags=["Metrics"],
    response_class=PlainTextResponse,
)
async def metrics() -> PlainTextResponse:
    """Expose Prometheus metrics for scraping."""
    return PlainTextResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
