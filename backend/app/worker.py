import sys
from typing import Any, Literal

from celery import Celery

from app.compatibility.errors import (
    IncompatibilityError,
    UnknownVersionError,
    UnsupportedOSError,
)
from app.compatibility.models import PackageConstraint, ResolvedEnvironment
from app.compatibility.resolver import CompatibilityResolver
from app.config import get_settings
from app.schemas.diagnostic import CompatibilityIssue, DiagnoseResponse

settings = get_settings()

import logging as _logging

_logger = _logging.getLogger(__name__)

if not settings.redis_url:
    if "pytest" in sys.modules:
        pass
    else:
        _logger.warning(
            "REDIS_URL is not configured. Falling back to Celery eager mode. "
            "All background tasks will run synchronously in-process. "
            "For production distributed deployments, set the REDIS_URL environment variable."
        )

celery_app = Celery(
    "envforage_worker",
    broker=settings.redis_url or "memory://",
    backend=settings.redis_url or "cache+memory://",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=not settings.redis_url,
    task_eager_propagates=not settings.redis_url,
)

import logging as _logging

_worker_logger = _logging.getLogger("celery.worker.pool")


@celery_app.on_after_configure.connect
def _warn_on_incompatible_pool(sender, **kwargs):  # type: ignore[no-untyped-def]
    """Log a warning if the worker uses a pool incompatible with asyncio.run()."""
    try:
        pool_cls = sender.conf.get("worker_pool", "prefork")
        if isinstance(pool_cls, str) and pool_cls in ("gevent", "eventlet"):
            _worker_logger.warning(
                "EnvForage tasks use asyncio.run() internally. "
                "Running with --pool=%s will cause RuntimeError. "
                "Use --pool=prefork (the default).",
                pool_cls,
            )
    except Exception:
        pass


@celery_app.task(name="run_diagnose_task")  # type: ignore[untyped-decorator]
def run_diagnose_task(
    report_id: str,
    report_data: dict[str, Any],
    target_os: Literal["LINUX", "WIN", "WSL"],
) -> dict[str, Any]:
    """
    Celery task that resolves an environment's dependencies against all profiles
    and returns a structured DiagnoseResponse as a dict.
    """
    resolver = CompatibilityResolver()

    issues: list[CompatibilityIssue] = []
    compatible_profiles: list[str] = []
    recommendations: list[str] = []

    import logging

    logger = logging.getLogger(__name__)

    active_python = report_data.get("active_python")
    if not active_python or not active_python.get("version"):
        raise ValueError("Diagnostic report is missing active_python version.")

    parts = active_python["version"].split(".")
    if len(parts) < 2:
        raise ValueError(f"Invalid Python version format: {active_python['version']}")
    active_python_version = f"{parts[0]}.{parts[1]}"

    cuda_version = (
        report_data.get("cuda", {}).get("version") if report_data.get("cuda") else None
    )
    rocm_version = (
        report_data.get("rocm", {}).get("version") if report_data.get("rocm") else None
    )

    # We will fetch profiles from DB directly here in the worker
    import asyncio

    from app.database import AsyncSessionLocal
    from app.schemas.profile import ProfileFilters
    from app.services.profile_service import list_profiles

    async def _fetch_profiles() -> list[Any]:
        all_profiles = []
        page = 1
        async with AsyncSessionLocal() as db:
            while True:
                batch, total = await list_profiles(
                    db,
                    ProfileFilters(
                        tags=None, os=None, cuda_required=None, page=page, limit=100
                    ),
                )
                all_profiles.extend(batch)
                if len(all_profiles) >= total:
                    break
                page += 1
        return all_profiles

    try:
        profiles = asyncio.run(_fetch_profiles())
    except Exception as e:
        logger.error(f"Worker component error: {e}")
        logger.exception("Failed to fetch profiles for run_diagnose_task")
        raise

    for profile in profiles:
        profile_slug: str = profile.slug
        os_support: list[str] = profile.os_support
        cuda_required: bool = profile.cuda_required
        rocm_required: bool = getattr(profile, "rocm_required", False)

        packages = []
        for pkg in sorted(profile.packages, key=lambda item: item.install_order):
            packages.append(
                PackageConstraint(
                    name=pkg.package_name,
                    version_spec=pkg.version_spec,
                    cuda_variant=pkg.cuda_variant,
                )
            )

        try:
            result = resolver.resolve(
                packages=packages,
                python_version=active_python_version,
                cuda_version=cuda_version,
                rocm_version=rocm_version,
                target_os=target_os,
                profile_slug=profile_slug,
                os_support=os_support,
                cuda_required=cuda_required,
                rocm_required=rocm_required,
            )

            if isinstance(result, ResolvedEnvironment):
                compatible_profiles.append(profile_slug)
                if result.warnings:
                    recommendations.extend(result.warnings)

        except IncompatibilityError as exc:
            issues.append(
                CompatibilityIssue(
                    severity="ERROR",
                    component=exc.component,
                    message=str(exc),
                    suggested_fix=exc.suggestion,
                    docs_url=exc.docs_url,
                )
            )
        except (UnknownVersionError, UnsupportedOSError) as exc:
            issues.append(
                CompatibilityIssue(
                    severity="ERROR",
                    component="compatibility",
                    message=str(exc),
                    suggested_fix=None,
                    docs_url=None,
                )
            )
        except Exception as e:
            logger.error(f"Worker error: {e}")
            logger.exception("Unexpected error resolving profile %s", profile_slug)
            raise

    response = DiagnoseResponse(
        report_id=report_id,
        compatible_profiles=compatible_profiles,
        issues=issues,
        recommendations=recommendations,
    )

    return response.model_dump()
