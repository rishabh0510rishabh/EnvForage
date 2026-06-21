"""Pydantic schemas for environment verification."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class VerificationCheckSchema(BaseModel):
    """Schema for a single verification check result."""

    check_name: str = Field(
        ...,
        description="Name or message of the verification check.",
        examples=["Python 3.10 detected"],
    )
    passed: bool = Field(
        ...,
        description="Whether the verification check passed.",
        examples=[True],
    )
    detail: str | None = Field(
        None,
        description="Optional additional detail or warning for the check.",
        examples=["WARN: CUDA version is newer than expected"],
    )

    model_config = ConfigDict(from_attributes=True)


class VerificationRequest(BaseModel):
    """Request schema for POST /api/v1/verify."""

    profile_id: uuid.UUID = Field(
        ...,
        description="Profile UUID associated with the verification result.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    report_id: uuid.UUID | None = Field(
        None,
        description="Optional diagnostic report UUID linked to this verification.",
        examples=["550e8400-e29b-41d4-a716-446655440001"],
    )
    raw_output: str = Field(
        ...,
        description="Raw terminal output produced by the verification script.",
        max_length=1_048_576,  # 1 MB limit to prevent abuse (enforced by middleware)
        examples=[
            "[PASS] Python 3.10 detected\n[WARN] CUDA version is newer than expected"
        ],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "profile_id": "550e8400-e29b-41d4-a716-446655440000",
                "report_id": "550e8400-e29b-41d4-a716-446655440001",
                "raw_output": (
                    "[PASS] Python 3.10 detected\n"
                    "[WARN] CUDA version is newer than expected"
                ),
            }
        }
    }


class VerificationResponse(BaseModel):
    """Response schema for POST /api/v1/verify."""

    result_id: uuid.UUID = Field(
        ...,
        description="Unique verification result UUID.",
        examples=["550e8400-e29b-41d4-a716-446655440002"],
    )
    profile_id: uuid.UUID = Field(
        ...,
        description="Profile UUID associated with the verification result.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    overall_status: str = Field(
        ...,
        description="Overall verification status. Either 'passed' or 'failed'.",
        examples=["passed"],
    )
    checks: list[VerificationCheckSchema] = Field(
        ...,
        description="Parsed verification checks from the raw output.",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "result_id": "550e8400-e29b-41d4-a716-446655440002",
                "profile_id": "550e8400-e29b-41d4-a716-446655440000",
                "overall_status": "passed",
                "checks": [
                    {
                        "check_name": "Python 3.10 detected",
                        "passed": True,
                        "detail": None,
                    }
                ],
            }
        },
    )

# ── ADD AT THE BOTTOM OF backend/app/schemas/verify.py ──────────────────



class PaginatedVerificationResponse(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    next_page_url: str | None = None
    prev_page_url: str | None = None
    results: list[VerificationResponse]
