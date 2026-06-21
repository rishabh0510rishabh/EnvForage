"""Health check endpoints — /api/v1/health.

Provides a readiness probe that verifies database and Redis connectivity.
Use for Kubernetes readiness/liveness probes.
"""

import asyncio
import datetime
import logging
import time

import psutil
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.deps import DB
from app.cache import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter()


async def ping_database(db: DB) -> dict:
    """Check database availability and latency."""
    start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000.0
        return {"status": "up", "latency_ms": latency}
    except Exception as exc:
        return {"status": "down", "error": str(exc)}


async def ping_redis() -> dict:
    """Check Redis availability and latency."""
    start = time.perf_counter()
    try:
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            latency = (time.perf_counter() - start) * 1000.0
            return {"status": "up", "latency_ms": latency}
        else:
            return {"status": "down", "error": "Redis not configured"}
    except Exception as exc:
        return {"status": "down", "error": str(exc)}


def get_system_metrics() -> dict:
    """Retrieve system resource usage metrics."""
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": cpu,
        "memory": {
            "total_gb": mem.total / (1024**3),
            "used_percent": mem.percent
        },
        "disk": {
            "total_gb": disk.total / (1024**3),
            "used_percent": disk.percent
        }
    }


@router.get(
    "/health",
    summary="Readiness health check",
    description="Verifies database and Redis connectivity for orchestrator probes.",
    tags=["Health"],
    responses={
        200: {"description": "All services healthy"},
        503: {"description": "One or more services degraded"},
    },
)
async def health_check(db: DB, response: Response) -> dict:
    """Check database and Redis availability.

    Returns 200 if all services are reachable, 503 if any are degraded.
    """
    db_status = "ok"
    cache_status = "ok"
    overall = "healthy"

    # Check database
    try:
        async with asyncio.timeout(2):
            await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Health check: database unreachable — %s", exc)
        db_status = "unavailable"
        overall = "degraded"

    # Check Redis
    try:
        redis = await get_redis_client()
        if redis:
            async with asyncio.timeout(1):
                await redis.ping()
        else:
            cache_status = "not_configured"
    except Exception as exc:
        logger.error("Health check: Redis unreachable — %s", exc)
        cache_status = "unavailable"
        overall = "degraded"

    if overall != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall,
        "db": db_status,
        "cache": cache_status,
    }


@router.get(
    "/health/deep",
    summary="Deep health check",
    description="Detailed status of all internal components and host resources.",
    tags=["Health"],
    responses={
        200: {"description": "All components healthy"},
        503: {"description": "One or more components degraded"},
    },
)
async def deep_health_check(db: DB, response: Response) -> dict:
    """Detailed health check validating resources and dependency services."""
    db_status = await ping_database(db)
    redis_status = await ping_redis()
    metrics = get_system_metrics()

    status_str = "healthy"

    # Degrade if DB or Redis is down, or if system resources are exhausted
    if (
        db_status["status"] == "down"
        or redis_status["status"] == "down"
        or metrics["memory"]["used_percent"] > 95.0
        or metrics["disk"]["used_percent"] > 95.0
    ):
        status_str = "degraded"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": status_str,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "components": {
            "database": db_status,
            "redis": redis_status,
        },
        "metrics": metrics,
    }
