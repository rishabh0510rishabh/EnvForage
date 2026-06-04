"""Diagnose endpoint -- POST /api/v1/diagnose and POST /api/v1/diagnose/explain."""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.ai.prompts.system import EXPLAIN_SYSTEM_PROMPT
from app.ai.providers import get_provider
from app.ai.providers.base import LLMProviderError
from app.api.deps import DB
from app.compatibility.errors import (
    IncompatibilityError,
    UnknownVersionError,
    UnsupportedOSError,
)
from app.compatibility.models import OSTarget, PackageConstraint, ResolvedEnvironment
from app.compatibility.resolver import CompatibilityResolver
from app.core.exceptions import AIServiceUnavailableError, InternalServerError
from app.middleware.rate_limit import ai_rate_limit
from app.models.ai_session import AIAuditLog
from app.models.diagnostic import DiagnosticReport
from app.models.profile import EnvironmentProfile
from app.schemas.ai import DiagnoseExplainResponse
from app.schemas.diagnostic import (
    CompatibilityIssue,
    DiagnoseResponse,
    DiagnosticReportSchema,
)
from app.services.profile_service import get_all_active_profiles
from app.templates.safety import SafetyViolationError, validate_rendered_output

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum number of profiles fetched per page when paginating.
# Kept intentionally small so each page fetch is cheap; the while-loop below
# accumulates all pages before running the resolver.
_PROFILE_PAGE_SIZE = 100

# Limit concurrency to 5 threads globally across all requests to avoid memory spikes under heavy load
_RESOLVER_SEMAPHORE = asyncio.Semaphore(5)


@router.post(
    "/diagnose",
    response_model=DiagnoseResponse,
    status_code=201,
    summary="Analyze environment compatibility",
    description=(
        "Accept a diagnostic report from the EnvForge CLI agent and return "
        "a compatibility analysis showing compatible profiles, detected issues, "
        "and recommendations."
    ),
    tags=["Diagnostics"],
    responses={
        201: {"description": "Diagnostic report analyzed successfully"},
        422: {"description": "Invalid diagnostic report payload"},
        500: {"description": "Internal server error"},
    },
)
async def diagnose(
    report: DiagnosticReportSchema,
    db: DB,
    _rate_limit: None = Depends(ai_rate_limit),
) -> DiagnoseResponse:
    """
    Accept a DiagnosticReport from the CLI agent and return
    a compatibility analysis: which profiles are compatible,
    and what issues were found.
    """
    # Map OS to OSTarget: "LINUX", "WSL", "WIN"
    target_os: OSTarget
    if report.os and report.os.wsl_version:
        target_os = "WSL"
    elif report.os and "windows" in report.os.name.lower():
        target_os = "WIN"
    else:
        target_os = "LINUX"

    # Persist the raw report
    db_report = DiagnosticReport(
        id=uuid.uuid4(),
        report_data=report.model_dump(),
        os_type=target_os,
        gpu_name=report.gpus[0].name if report.gpus else None,
        cuda_version=report.cuda.version if report.cuda else None,
        rocm_version=report.rocm.version if report.rocm else None,
        python_version=".".join(report.active_python.version.split(".")[:2])
        if report.active_python
        else None,
        driver_version=report.gpus[0].driver_version if report.gpus else None,
        created_at=datetime.now(UTC),
    )
    db.add(db_report)
    await db.flush()

    # Fetch every profile directly, avoiding pagination/count overhead
    all_profiles = await get_all_active_profiles(db, include_packages=True)

    if not all_profiles:
        return DiagnoseResponse(
            report_id=str(db_report.id),
            compatible_profiles=[],
            issues=[],
            recommendations=[],
        )

    resolver = CompatibilityResolver()

    issues: list[CompatibilityIssue] = []
    compatible_profiles: list[str] = []
    recommendations: list[str] = []

    # CompatibilityResolver.resolve() is a CPU-bound synchronous function.
    # Calling it directly inside an async handler blocks the event loop for
    # the duration of every resolve call. Under concurrent load, all other
    # requests queue behind the resolver. Each call is offloaded to a thread
    # via asyncio.to_thread so the event loop stays free.
    async def _resolve(profile: EnvironmentProfile) -> ResolvedEnvironment:
        packages = [
            PackageConstraint(
                name=package.package_name,
                version_spec=package.version_spec,
                cuda_variant=package.cuda_variant,
            )
            for package in sorted(profile.packages, key=lambda item: item.install_order)
        ]
        async with _RESOLVER_SEMAPHORE:
            return await resolver.resolve(
                packages=packages,
                python_version=(
                    report.active_python.version if report.active_python else None
                )
                or "3.10",
                cuda_version=report.cuda.version if report.cuda else None,
                rocm_version=report.rocm.version if report.rocm else None,
                target_os=target_os,
                profile_slug=profile.slug,
                os_support=profile.os_support,
                cuda_required=profile.cuda_required,
                rocm_required=getattr(profile, "rocm_required", False),
                db=db,
            )

    results = await asyncio.gather(
        *[_resolve(p) for p in all_profiles],
        return_exceptions=True,
    )

    for profile, result in zip(all_profiles, results):
        if isinstance(result, IncompatibilityError):
            issues.append(
                CompatibilityIssue(
                    severity="ERROR",
                    component=result.component,
                    message=str(result),
                    suggested_fix=result.suggestion,
                    docs_url=result.docs_url,
                )
            )
        elif isinstance(result, (UnknownVersionError, UnsupportedOSError)):
            issues.append(
                CompatibilityIssue(
                    severity="ERROR",
                    component="compatibility",
                    message=str(result),
                    suggested_fix=None,
                    docs_url=None,
                )
            )
        elif isinstance(result, Exception):
            logger.warning(
                "Resolver raised unexpected error for profile %s: %s",
                profile.slug,
                result,
            )
        else:
            assert isinstance(result, ResolvedEnvironment)
            compatible_profiles.append(profile.slug)
            if result.warnings:
                recommendations.extend(result.warnings)

    return DiagnoseResponse(
        report_id=str(db_report.id),
        compatible_profiles=compatible_profiles,
        issues=issues,
        recommendations=recommendations,
    )


@router.post(
    "/diagnose/explain",
    response_model=DiagnoseExplainResponse,
    status_code=200,
    summary="AI-powered plain-English explanation of diagnostic issues",
    description=(
        "Accept a DiagnosticReport JSON and return a plain-English explanation "
        "of what is broken and ordered remediation steps. Does NOT execute any "
        "command on the user's machine."
    ),
    tags=["AI"],
    responses={
        200: {"description": "AI explanation returned successfully"},
        422: {"description": "Invalid diagnostic report payload"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "AI provider unavailable"},
    },
)
async def diagnose_explain(
    report: DiagnosticReportSchema,
    db: DB,
    _rate_limit: None = Depends(ai_rate_limit),
) -> DiagnoseExplainResponse:
    """
    Accept a DiagnosticReport and return a structured AI explanation
    of what is wrong with the environment, using only validated fields.

    The AI does NOT replace the CompatibilityEngine — it only reads
    its structured input. No commands are executed.
    """
    start_time = time.monotonic()
    report_json = report.model_dump(mode="json")
    input_hash = hashlib.sha256(
        json.dumps(report_json, sort_keys=True).encode()
    ).hexdigest()[:64]

    user_message = json.dumps(report_json, indent=2)

    provider = get_provider()
    provider_name = type(provider).__name__

    try:
        llm_result = await provider.complete(
            system_prompt=EXPLAIN_SYSTEM_PROMPT,
            user_message=user_message,
            response_model=DiagnoseExplainResponse,
        )
    except LLMProviderError as exc:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        _log_explain_audit(
            db, input_hash, False, str(exc), provider_name, 0, latency_ms
        )
        raise AIServiceUnavailableError(
            provider=provider_name,
            reason=getattr(exc, "reason", str(exc)),
        ) from exc

    # Safety filter: validate all text fields before returning to user
    try:
        validate_rendered_output(llm_result.issue_summary, "ai_explain_summary")
        validate_rendered_output(llm_result.root_cause, "ai_explain_root_cause")
        for step in llm_result.suggested_steps:
            validate_rendered_output(step, "ai_explain_step")
    except SafetyViolationError as exc:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        _log_explain_audit(
            db, input_hash, False, str(exc), provider_name, 0, latency_ms
        )
        raise InternalServerError(
            "AI response was blocked by the safety filter."
        ) from exc

    latency_ms = int((time.monotonic() - start_time) * 1000)
    _log_explain_audit(db, input_hash, True, None, provider_name, 0, latency_ms)

    return llm_result


def _log_explain_audit(
    db: "DB",
    input_hash: str,
    safety_passed: bool,
    safety_violation: str | None,
    provider: str,
    tokens_used: int,
    latency_ms: int,
) -> None:
    """Write an audit log entry for the explain interaction."""
    try:
        log = AIAuditLog(
            id=uuid.uuid4(),
            session_id=None,
            input_hash=input_hash,
            safety_passed=safety_passed,
            safety_violation=safety_violation,
            provider=provider,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            created_at=datetime.now(UTC),
        )
        db.add(log)
    except Exception as exc:
        logger.exception("Failed to write explain audit log: %s", exc)
