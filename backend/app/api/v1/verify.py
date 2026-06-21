"""Verify endpoint — POST /api/v1/verify."""
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import DB
from app.middleware.rate_limit import general_rate_limit
from app.models.diagnostic import VerificationCheck, VerificationResult
from app.models.profile import EnvironmentProfile
from app.schemas.verify import (
    VerificationCheckSchema,
    VerificationRequest,
    VerificationResponse,
)

router = APIRouter()

# Regex to strip ANSI escape codes (colors, etc.)
ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def parse_output(text: str) -> tuple[str, list[dict[str, Any]]]:
    """
    Parse raw terminal output from verification scripts.
    Extracts [PASS], [FAIL], and [WARN] indicators.
    """
    clean_text = ANSI_ESCAPE.sub("", text)
    checks: list[dict[str, Any]] = []
    overall_status = "passed"

    lines = clean_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match lines like: [PASS] Python 3.10 (Python 3.10.12)
        match = re.match(r"\[(PASS|FAIL|WARN)\]\s+(.*)", line)
        if match:
            level = match.group(1)
            message = match.group(2)

            if level == "PASS":
                checks.append({"name": message, "passed": True, "detail": None})
            elif level == "FAIL":
                checks.append({"name": message, "passed": False, "detail": None})
                overall_status = "failed"
            elif level == "WARN":
                if checks:
                    # Append warning to the detail of the previous check
                    prev = checks[-1]
                    if prev["detail"]:
                        prev["detail"] += f" | WARN: {message}"
                    else:
                        prev["detail"] = f"WARN: {message}"
                else:
                    # If no previous check, record as a passed check with warning detail
                    checks.append(
                        {"name": message, "passed": True, "detail": f"WARN: {message}"}
                    )

    return overall_status, checks


@router.post(
    "/verify",
    response_model=VerificationResponse,
    status_code=201,
    summary="Verify environment setup output",
    description=(
        "Parse raw verification script output, extract PASS, FAIL, and WARN "
        "checks, and store the structured verification result."
    ),
    tags=["Verification"],
    responses={
        201: {"description": "Verification results stored successfully"},
        404: {"description": "Profile not found"},
        422: {"description": "Request validation error"},
    },
)
async def verify_environment(
    payload: VerificationRequest,
    db: DB,
    _rate_limit: None = Depends(general_rate_limit),
) -> VerificationResponse:
    """
    Ingest and parse the output of a verification script.
    Stores results in verification_results and verification_checks tables.
    """
    # 1. Validate profile exists
    profile = await db.get(EnvironmentProfile, payload.profile_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "PROFILE_NOT_FOUND",
                    "message": f"Profile with ID {payload.profile_id} not found",
                }
            },
        )

    # 2. Parse the raw output
    overall_status, parsed_checks = parse_output(payload.raw_output)

    # 3. Create VerificationResult record
    db_result = VerificationResult(
        id=uuid.uuid4(),
        report_id=payload.report_id,
        profile_id=payload.profile_id,
        overall_status=overall_status,
        created_at=datetime.now(UTC),
    )
    db.add(db_result)

    # 4. Create VerificationCheck records for each parsed check
    for check in parsed_checks:
        db_check = VerificationCheck(
            id=uuid.uuid4(),
            result_id=db_result.id,
            check_name=check["name"][:128],  # Ensure it fits in String(128)
            passed=check["passed"],
            detail=check["detail"],
        )
        db.add(db_check)

    # Flush to ensure IDs are generated and constraints are checked
    await db.flush()
    await db.commit()

    return VerificationResponse(
        result_id=db_result.id,
        profile_id=db_result.profile_id,
        overall_status=db_result.overall_status,
        checks=[
            VerificationCheckSchema(
                check_name=c["name"], passed=c["passed"], detail=c["detail"]
            )
            for c in parsed_checks
        ],
    )
