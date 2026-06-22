"""
Script generation service — orchestrates Compatibility Engine + Template Engine.
"""

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_redis_client
from app.compatibility.models import (
    PackageConstraint,
    ResolvedEnvironment,
)
from app.compatibility.models import (
    ResolvedPackage as CompatibilityResolvedPackage,
)
from app.compatibility.resolver import CompatibilityResolver
from app.config import get_settings
from app.models.profile import EnvironmentProfile
from app.models.script_job import GeneratedScript, ScriptGenerationJob
from app.schemas.script import (
    GenerationRequest,
    GenerationResponse,
    ScriptPreview,
)
from app.schemas.script import (
    ResolvedPackage as ResponseResolvedPackage,
)
from app.templates.engine import TemplateRenderer
from app.templates.models import TemplateContext

_resolver = CompatibilityResolver()
_renderer = TemplateRenderer()
_logger = logging.getLogger(__name__)

_RESOLVER_CACHE_PREFIX = "compatibility_resolver:v1"


def _resolver_cache_ttl_seconds() -> int:
    return max(get_settings().resolver_cache_ttl_seconds, 1)


def _resolver_cache_key(
    profile: EnvironmentProfile,
    request: GenerationRequest,
    constraints: list[PackageConstraint],
) -> str:
    """Build a stable cache key for deterministic resolver inputs."""
    payload = {
        "profile_slug": profile.slug,
        "target_os": request.target_os,
        "python_version": request.python_version,
        "cuda_version": request.cuda_version,
        "overrides": request.overrides or {},
        "os_support": sorted(profile.os_support),
        "cuda_required": profile.cuda_required,
        "packages": [
            {
                "name": constraint.name,
                "version_spec": constraint.version_spec,
                "cuda_variant": constraint.cuda_variant,
            }
            for constraint in constraints
        ],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"{_RESOLVER_CACHE_PREFIX}:{digest}"


def _resolved_environment_from_dict(data: dict[str, Any]) -> ResolvedEnvironment:
    return ResolvedEnvironment(
        python_version=data["python_version"],
        cuda_version=data.get("cuda_version"),
        rocm_version=data.get("rocm_version"),
        target_os=data["target_os"],
        packages=[
            CompatibilityResolvedPackage(
                name=package["name"],
                version=package["version"],
                cuda_variant=package.get("cuda_variant"),
            )
            for package in data.get("packages", [])
        ],
        warnings=list(data.get("warnings", [])),
    )


async def _get_cached_resolved_environment(
    cache_key: str,
) -> ResolvedEnvironment | None:
    try:
        redis = await get_redis_client()
    except Exception as exc:  # pragma: no cover - defensive cache fallback
        _logger.warning("Redis resolver cache client unavailable: %s", exc)
        return None

    if redis is None:
        return None

    try:
        cached = await redis.get(cache_key)
    except Exception as exc:  # pragma: no cover - defensive cache fallback
        _logger.warning("Redis resolver cache read failed: %s", exc)
        return None

    if cached is None:
        return None

    try:
        return _resolved_environment_from_dict(json.loads(cached))
    except (KeyError, TypeError, ValueError) as exc:
        _logger.warning("Ignoring invalid resolver cache payload: %s", exc)
        return None


async def _cache_resolved_environment(
    cache_key: str,
    resolved: ResolvedEnvironment,
) -> None:
    try:
        redis = await get_redis_client()
    except Exception as exc:  # pragma: no cover - defensive cache fallback
        _logger.warning("Redis resolver cache client unavailable: %s", exc)
        return

    if redis is None:
        return

    try:
        await redis.set(
            cache_key,
            json.dumps(resolved.to_dict(), sort_keys=True),
            ex=_resolver_cache_ttl_seconds(),
        )
    except Exception as exc:  # pragma: no cover - defensive cache fallback
        _logger.warning("Redis resolver cache write failed: %s", exc)


async def generate_scripts(
    db: AsyncSession,
    profile: EnvironmentProfile,
    request: GenerationRequest,
) -> GenerationResponse:
    """
    Main script generation pipeline:
    1. Build PackageConstraints from profile
    2. Run CompatibilityResolver
    3. Render templates
    4. Persist job + scripts to DB
    5. Return GenerationResponse
    """
    # Step 1: Build constraints from profile packages
    constraints = [
        PackageConstraint(
            name=pkg.package_name,
            version_spec=pkg.version_spec,
            cuda_variant=pkg.cuda_variant,
        )
        for pkg in sorted(profile.packages, key=lambda p: p.install_order)
    ]

    # Step 2: Resolve compatible versions
    cache_key = _resolver_cache_key(profile, request, constraints)
    resolved = await _get_cached_resolved_environment(cache_key)
    if resolved is None:
        resolved = await _resolver.resolve(
            packages=constraints,
            python_version=request.python_version,
            cuda_version=request.cuda_version,
            target_os=request.target_os,
            profile_slug=profile.slug,
            os_support=list(profile.os_support),
            cuda_required=profile.cuda_required,
            overrides=request.overrides,
            db=db,
        )
        await _cache_resolved_environment(cache_key, resolved)

    # Step 3: Render templates
    ctx = TemplateContext(
        profile_id=profile.slug,
        profile_name=profile.name,
        resolved=resolved,
        warnings=resolved.warnings,
        use_uv=request.use_uv,
        use_micromamba=request.use_micromamba,
    )
    render_results = await _renderer.render_all(request.output_formats, ctx)

    # Step 4: Persist job + scripts
    job = ScriptGenerationJob(
        id=uuid.uuid4(),
        profile_id=profile.id,
        target_os=request.target_os,
        python_version=request.python_version,
        cuda_version=request.cuda_version,
        overrides=request.overrides or {},
        status="completed",
        resolved_env=resolved.to_dict(),
        completed_at=datetime.now(UTC),
    )
    db.add(job)

    for rr in render_results:
        db.add(
            GeneratedScript(
                id=uuid.uuid4(),
                job_id=job.id,
                filename=rr.filename,
                content=rr.content,
                size_bytes=rr.size_bytes,
            )
        )

    await db.flush()  # Get job.id without committing transaction

    # Step 5: Build response
    return GenerationResponse(
        job_id=job.id,
        status="completed",
        profile_slug=profile.slug,
        target_os=request.target_os,
        python_version=request.python_version,
        cuda_version=request.cuda_version,
        resolved_packages=[
            ResponseResolvedPackage(
                name=p.name,
                version=p.version,
                cuda_variant=p.cuda_variant,
            )
            for p in resolved.packages
        ],
        scripts=[
            ScriptPreview(
                filename=rr.filename,
                content=rr.content,
                size_bytes=rr.size_bytes,
            )
            for rr in render_results
        ],
        warnings=resolved.warnings,
        download_url=f"/api/v1/scripts/{job.id}/download",
    )
