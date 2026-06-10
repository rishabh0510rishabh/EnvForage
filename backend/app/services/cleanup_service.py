"""Background cleanup service for expired script generation records."""

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from prometheus_client import Counter, Gauge
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.script_job import GeneratedScript, ScriptGenerationJob

logger = logging.getLogger(__name__)

SCRIPT_GENERATION_JOBS_RETENTION_DAYS = 30
GENERATED_SCRIPTS_RETENTION_DAYS = 7

# Cleanup Task Metrics

CLEANUP_RUNS_TOTAL = Counter(
    "cleanup_runs_total",
    "Total number of cleanup task executions",
    ["status"],
)

CLEANUP_LAST_RUN_TIMESTAMP = Gauge(
    "cleanup_last_run_timestamp_seconds",
    "Unix timestamp of the last cleanup task attempt",
)

CLEANUP_LAST_RUN_SUCCESS = Gauge(
    "cleanup_last_run_success",
    "1 if the last cleanup run succeeded, 0 if it failed",
)


async def delete_expired_records(db: AsyncSession) -> dict[str, Any]:
    """Delete expired records based on retention policy."""
    now = datetime.now(UTC)
    jobs_cutoff = now - timedelta(days=SCRIPT_GENERATION_JOBS_RETENTION_DAYS)
    scripts_cutoff = now - timedelta(days=GENERATED_SCRIPTS_RETENTION_DAYS)

    # Delete generated_scripts first (child records)
    scripts_result = await db.execute(
        delete(GeneratedScript).where(GeneratedScript.created_at < scripts_cutoff)
    )
    deleted_scripts: int = scripts_result.rowcount  # type: ignore[attr-defined]

    # Delete script_generation_jobs (parent records)
    jobs_result = await db.execute(
        delete(ScriptGenerationJob).where(ScriptGenerationJob.created_at < jobs_cutoff)
    )
    deleted_jobs: int = jobs_result.rowcount  # type: ignore[attr-defined]

    await db.commit()

    summary: dict[str, Any] = {
        "deleted_scripts": deleted_scripts,
        "deleted_jobs": deleted_jobs,
        "ran_at": now.isoformat(),
    }
    logger.info(f"Cleanup completed: {summary}")
    return summary


async def run_cleanup() -> None:
    """Entry point for the scheduler — manages its own DB session."""
    logger.info("Running scheduled database cleanup...")
    CLEANUP_LAST_RUN_TIMESTAMP.set(time.time())
    async with AsyncSessionLocal() as db:
        try:
            result = await delete_expired_records(db)
            logger.info(f"Cleanup result: {result}")
            CLEANUP_RUNS_TOTAL.labels(status="success").inc()
            CLEANUP_LAST_RUN_SUCCESS.set(1)
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}", exc_info=True)
            await db.rollback()
            CLEANUP_RUNS_TOTAL.labels(status="failure").inc()
            CLEANUP_LAST_RUN_SUCCESS.set(0)
            raise
