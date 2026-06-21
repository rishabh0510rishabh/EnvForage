"""
FastAPI application factory and lifespan management.
"""

import asyncio
import sys
import typing
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routers import media_upload, spatial_query
from app.api.v1 import (
    authentication,
    compatibility,
    diagnose,
    feedback,
    profiles,
    recommend,
    repair,
    scripts,
    troubleshoot,
    verify,
)
from app.api.v1 import (
    health as health_v1,
)
from app.api.v1.admin.matrix import router as admin_matrix_router
from app.cache import get_redis_client
from app.config import get_settings
from app.core.handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.stream_tracker import StreamTracker
from app.database import AsyncSessionLocal
from app.middleware.metrics import setup_metrics
from app.middleware.payload_size import PayloadSizeLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.cleanup_service import run_cleanup
from app.services.sync_service import matrix_sync_loop

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    settings = get_settings()
    logger_instance = structlog.get_logger(__name__)

    logger_instance.info(
        "EnvForage API starting",
        version=settings.app_version,
        environment=settings.environment,
    )
    # Track in-flight SSE streams so shutdown can drain them gracefully.
    app.state.stream_tracker = StreamTracker()

    # ── Background cleanup scheduler ─────────────────────────
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_cleanup,
        trigger="interval",
        hours=24,
        id="db_cleanup",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger_instance.info("Cleanup scheduler started (runs every 24h)")

    sync_task = None
    if "pytest" not in sys.modules and settings.run_sync_loop:
        sync_task = asyncio.create_task(matrix_sync_loop(AsyncSessionLocal))

    yield

    # Let active SSE streams finish before tearing resources down
    # (e.g. on SIGTERM during a rolling update) — see issue #192.
    drained = await app.state.stream_tracker.drain(
        settings.graceful_shutdown_timeout_seconds
    )
    if not drained:
        logger_instance.warning(
            "Graceful shutdown timed out while waiting for active streams"
        )

    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass

    scheduler.shutdown(wait=False)
    logger_instance.info("EnvForage API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    _is_prod = settings.environment == "production"
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Production-grade ML/AI environment provisioning platform. "
            "Generates setup scripts, diagnoses environments, and provides "
            "AI-assisted troubleshooting."
        ),
        docs_url=None if _is_prod else "/api/docs",
        redoc_url=None if _is_prod else "/api/redoc",
        openapi_url=None if _is_prod else "/api/openapi.json",
        lifespan=lifespan,
    )
    setup_logging()

    # Register centralized exception handlers from app.core.handlers.
    # This keeps API error formatting and logging behavior consistent
    # across the application through a single implementation.
    register_exception_handlers(app)
    # ── CORS ─────────────────────────────────────────────────

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(PayloadSizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # ── Prometheus Metrics ────────────────────────────────────
    setup_metrics(app)

    # ── Routers ───────────────────────────────────────────────
    app.include_router(profiles.router, prefix="/api/v1", tags=["profiles"])
    app.include_router(scripts.router, prefix="/api/v1", tags=["scripts"])
    app.include_router(diagnose.router, prefix="/api/v1", tags=["diagnose"])
    app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
    app.include_router(troubleshoot.router, prefix="/api/v1", tags=["ai"])
    app.include_router(repair.router, prefix="/api/v1", tags=["ai"])
    app.include_router(verify.router, prefix="/api/v1", tags=["verify"])
    app.include_router(compatibility.router, prefix="/api/v1", tags=["compatibility"])
    app.include_router(authentication.router, prefix="/api/v1", tags=["auth"])
    app.include_router(recommend.router, prefix="/api/v1", tags=["recommendations"])
    app.include_router(admin_matrix_router, prefix="/api/v1", tags=["admin-matrix"])
    app.include_router(media_upload.router, prefix="/api/v1", tags=["media"])
    app.include_router(spatial_query.router, prefix="/api/v1", tags=["locations"])
    app.include_router(health_v1.router, prefix="/api/v1", tags=["health"])

    # ── Health check ──────────────────────────────────────────
    @app.get("/health", include_in_schema=False)
    async def health() -> JSONResponse:
        db_status = "ok"
        redis_status = "ok"
        overall = "healthy"
        try:
            async with asyncio.timeout(2):
                async with AsyncSessionLocal() as session:
                    await session.execute(text("SELECT 1"))
        except Exception as e:
            logger.error(f"Main app error: {e}")
            db_status = "unavailable"
            overall = "degraded"
        try:
            async with asyncio.timeout(
                1
            ):  # Enforce 1s timeout to prevent TCP blackhole hang
                redis = await get_redis_client()
                if redis is None:
                    redis_status = "not_configured"
                else:
                    await typing.cast(typing.Any, redis).ping()
        except TimeoutError:
            redis_status = "unavailable"
            overall = "degraded"
        except Exception as e:
            import logging
            logging.error(f"Main shutdown error: {e}")
            redis_status = "unavailable"
            overall = "degraded"
        return JSONResponse(
            status_code=200 if overall == "healthy" else 503,
            content={
                "status": overall,
                "version": settings.app_version,
                "services": {
                    "database": db_status,
                    "redis": redis_status,
                },
            },
        )

    return app


app = create_app()

