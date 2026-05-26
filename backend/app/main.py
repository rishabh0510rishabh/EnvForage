"""
FastAPI application factory and lifespan management.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import (
    compatibility,
    diagnose,
    profiles,
    repair,
    scripts,
    troubleshoot,
    verify,
)
from app.cache import get_redis_client
from app.config import get_settings
from app.core.handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    settings = get_settings()

    logger.info(
        "application_startup",
        version=settings.app_version,
        environment=settings.environment,
    )

    yield

    logger.info("application_shutdown")


def create_app() -> FastAPI:
    configure_logging()

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Production-grade ML/AI environment provisioning platform. "
            "Generates setup scripts, diagnoses environments, and provides "
            "AI-assisted troubleshooting."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    # ── CORS ─────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────
    app.include_router(profiles.router, prefix="/api/v1", tags=["profiles"])
    app.include_router(scripts.router, prefix="/api/v1", tags=["scripts"])
    app.include_router(diagnose.router, prefix="/api/v1", tags=["diagnose"])
    app.include_router(troubleshoot.router, prefix="/api/v1", tags=["ai"])
    app.include_router(repair.router, prefix="/api/v1", tags=["ai"])
    app.include_router(verify.router, prefix="/api/v1", tags=["verify"])
    app.include_router(
        compatibility.router,
        prefix="/api/v1",
        tags=["compatibility"],
    )

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

        except Exception:
            db_status = "unavailable"
            overall = "degraded"

        try:
            async with asyncio.timeout(2):
                redis = await get_redis_client()

                if redis is None:
                    redis_status = "not_configured"
                else:
                    await redis.ping()  # type: ignore[misc]

        except Exception:
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
