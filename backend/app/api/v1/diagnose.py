"""Diagnose endpoint -- POST /api/v1/diagnose and POST /api/v1/diagnose/explain."""

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
from app.compatibility.models import OSTarget
from app.core.exceptions import AIServiceUnavailableError, InternalServerError
from app.middleware.rate_limit import ai_rate_limit
from app.models.ai_session import AIAuditLog
from app.models.diagnostic import DiagnosticReport
from app.schemas.ai import DiagnoseExplainResponse
from app.schemas.diagnostic import (
    DiagnoseResponse,
    DiagnoseTaskStatus,
    DiagnosticReportSchema,
    TaskResponse,
)
from app.templates.safety import SafetyViolationError, validate_rendered_output
from app.worker import run_diagnose_task

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum number of profiles fetched per page when paginating.
# Kept intentionally small so each page fetch is cheap; the while-loop below
# accumulates all pages before running the resolver.
_PROFILE_PAGE_SIZE = 100


@router.post(
    "/diagnose",
    response_model=TaskResponse,
    status_code=202,
    summary="Analyze environment compatibility (Async)",
    description=(
        "Accept a diagnostic report from the EnvForge CLI agent, dispatch a Celery task, "
        "and return a task_id for polling."
    ),
    tags=["Diagnostics"],
    responses={
        202: {"description": "Diagnostic report queued successfully"},
        422: {"description": "Invalid diagnostic report payload"},
        500: {"description": "Internal server error"},
    },
)
async def diagnose(
    report: DiagnosticReportSchema,
    db: DB,
    _rate_limit: None = Depends(ai_rate_limit),
) -> TaskResponse:
    """
    Accept a DiagnosticReport from the CLI agent, offload compatibility
    analysis to Celery, and return a task ID.
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
    await db.commit()

    task = run_diagnose_task.delay(
        str(db_report.id),
        report.model_dump(),
        target_os,
    )

    return TaskResponse(task_id=task.id, status=task.status)


@router.get(
    "/diagnose/status/{task_id}",
    response_model=DiagnoseTaskStatus,
    summary="Poll diagnostic task status",
    tags=["Diagnostics"],
)
async def diagnose_status(task_id: str) -> DiagnoseTaskStatus:
    """Check the status of a queued diagnostic analysis."""
    from app.worker import celery_app

    result = celery_app.AsyncResult(task_id)
    if result.ready():
        if result.successful():
            return DiagnoseTaskStatus(
                task_id=task_id,
                status=result.status,
                result=DiagnoseResponse(**result.result),
            )
        else:
            return DiagnoseTaskStatus(
                task_id=task_id, status=result.status, error=str(result.result)
            )
    return DiagnoseTaskStatus(task_id=task_id, status=result.status)


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
