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

celery_app = Celery(
    "envforge_worker",
    broker=settings.redis_url or "redis://localhost:6379/0",
    backend=settings.redis_url or "redis://localhost:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="run_diagnose_task")  # type: ignore
def run_diagnose_task(report_id: str, report_data: dict[str, Any], target_os: Literal['LINUX', 'WIN', 'WSL']) -> dict[str, Any]:
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

    cuda_version = report_data.get("cuda", {}).get("version") if report_data.get("cuda") else None
    rocm_version = report_data.get("rocm", {}).get("version") if report_data.get("rocm") else None

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
                    ProfileFilters(tags=None, os=None, cuda_required=None, page=page, limit=100),
                )
                all_profiles.extend(batch)
                if len(all_profiles) >= total:
                    break
                page += 1
        return all_profiles

    try:
        profiles = asyncio.run(_fetch_profiles())
    except Exception:
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
        except Exception:
            logger.exception("Unexpected error resolving profile %s", profile_slug)
            raise

    response = DiagnoseResponse(
        report_id=report_id,
        compatible_profiles=compatible_profiles,
        issues=issues,
        recommendations=recommendations,
    )

    return response.model_dump()
