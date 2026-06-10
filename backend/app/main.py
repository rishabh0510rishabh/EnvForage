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

from app.api.v1 import (
    authentication,
    compatibility,
    diagnose,
    profiles,
    recommend,
    repair,
    scripts,
    troubleshoot,
    verify,
)
from app.api.v1.admin.matrix import router as admin_matrix_router
from app.api.routers import feature_issue_803, feature_issue_804
from app.cache import get_redis_client
from app.config import get_settings
from app.core.handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.database import AsyncSessionLocal
from app.middleware.metrics import setup_metrics
from app.middleware.payload_size import PayloadSizeLimitMiddleware
from app.services.cleanup_service import run_cleanup
from app.services.sync_service import matrix_sync_loop

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    settings = get_settings()
    logger_instance = structlog.get_logger(__name__)

    logger_instance.info(
        "EnvForge API starting",
        version=settings.app_version,
        environment=settings.environment,
    )
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

    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass

    scheduler.shutdown(wait=False)
    logger_instance.info("EnvForge API shutting down")


def create_app() -> FastAPI:
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
    setup_logging()
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

    # ── Prometheus Metrics ────────────────────────────────────
    setup_metrics(app)

    # ── Routers ───────────────────────────────────────────────
    app.include_router(profiles.router, prefix="/api/v1", tags=["profiles"])
    app.include_router(scripts.router, prefix="/api/v1", tags=["scripts"])
    app.include_router(diagnose.router, prefix="/api/v1", tags=["diagnose"])
    app.include_router(troubleshoot.router, prefix="/api/v1", tags=["ai"])
    app.include_router(repair.router, prefix="/api/v1", tags=["ai"])
    app.include_router(verify.router, prefix="/api/v1", tags=["verify"])
    app.include_router(compatibility.router, prefix="/api/v1", tags=["compatibility"])
    app.include_router(authentication.router, prefix="/api/v1", tags=["auth"])
    app.include_router(recommend.router, prefix="/api/v1", tags=["recommendations"])
    app.include_router(admin_matrix_router, prefix="/api/v1", tags=["admin-matrix"])
    app.include_router(feature_issue_803.router, prefix="/api/v1", tags=["media"])
    app.include_router(feature_issue_804.router, prefix="/api/v1", tags=["locations"])

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


# --- Advanced Application State Manager ---
import enum
import time
from typing import Dict, Any, Callable

class AppState(enum.Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"

class GracefulShutdownManager:
    def __init__(self):
        self.state = AppState.INITIALIZING
        self.hooks: list[Callable] = []
        self.start_time = time.time()
        self.components: Dict[str, str] = {}

    def register_hook(self, func: Callable):
        self.hooks.append(func)

    def register_component(self, name: str, status: str = "ok"):
        self.components[name] = status

    def transition(self, new_state: AppState):
        import logging
        logging.info(f"App State Transition: {self.state.name} -> {new_state.name}")
        self.state = new_state

    async def execute_shutdown(self):
        self.transition(AppState.SHUTTING_DOWN)
        import logging
        
        for hook in reversed(self.hooks):
            try:
                logging.info(f"Executing shutdown hook: {hook.__name__}")
                import asyncio
                if asyncio.iscoroutinefunction(hook):
                    await asyncio.wait_for(hook(), timeout=5.0)
                else:
                    hook()
            except Exception as e:
                logging.error(f"Shutdown hook {hook.__name__} failed: {e}")
                
        self.transition(AppState.TERMINATED)
        logging.info(f"Uptime: {time.time() - self.start_time:.2f} seconds")

global_shutdown_manager = GracefulShutdownManager()


# --- Global Exception Handlers ---
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger("GlobalErrorHandler")

# Need to attach this after app creation
def setup_exception_handlers(app):
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Unprocessable Entity",
                "details": exc.errors(),
                "path": request.url.path
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred while processing your request.",
                "path": request.url.path
            }
        )
