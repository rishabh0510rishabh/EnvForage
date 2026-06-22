"""
AI Layer — Pydantic models for request/response schemas.

Changes (Confidence Scoring Issue):
- Added FixConfidenceLevel enum (HIGH / MEDIUM / LOW)
- Extended SuggestedFix with per-fix confidence fields:
    confidence_level, confidence_score, is_matrix_backed,
    uncertainty_reason, fallback_recommendation
- TroubleshootResponse.confidence (overall) kept for backward compat
- Added suppressed_fix_count field to TroubleshootResponse
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

# Confidence primitives


class FixConfidenceLevel(StrEnum):
    """
    HIGH   — Fix directly traceable to a known entry in the CompatibilityEngine
             matrix (CUDA ↔ driver ↔ framework). LLM is acting as lookup.
    MEDIUM — Fix inferred from DiagnosticReport with partial evidence.
    LOW    — Fix is speculative; LLM is generalizing without a direct reference.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LLMResponseMeta(BaseModel):
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


# Core AI models


class SuggestedFix(BaseModel):
    """A single ordered remediation step returned by the AI layer."""

    # Existing fields (unchanged)
    step: int = Field(..., ge=1)
    title: str = Field(..., min_length=3, max_length=200)
    description: str
    severity: Literal["CRITICAL", "WARNING", "INFO"]
    safe_commands: list[str] = Field(
        default_factory=list,
        description="READ-ONLY diagnostic commands only (e.g. nvidia-smi). Never install/uninstall.",
    )
    repair_template_id: str | None = None

    # New confidence fields
    confidence_level: FixConfidenceLevel | None = Field(
        default=None,
        description="HIGH = matrix-backed, MEDIUM = inferred, LOW = speculative",
    )
    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Numeric confidence: HIGH>=0.75, MEDIUM in [0.40,0.75), LOW<0.40",
    )
    is_matrix_backed: bool | None = Field(
        default=None,
        description="True only when fix is directly traceable to CompatibilityEngine matrix",
    )
    uncertainty_reason: str | None = Field(
        default=None,
        description="Required when confidence_level is MEDIUM or LOW",
    )
    fallback_recommendation: str | None = Field(
        default=None,
        description="What user should try if this fix fails. Required for LOW fixes.",
    )

    @field_validator("uncertainty_reason")
    @classmethod
    def uncertainty_required_for_non_high(
        cls, v: str | None, info: ValidationInfo
    ) -> str | None:
        level = info.data.get("confidence_level")
        if level is None:
            return v  # skip if confidence fields not provided
        if level in (FixConfidenceLevel.MEDIUM, FixConfidenceLevel.LOW):
            if not v or not v.strip():
                raise ValueError(
                    f"uncertainty_reason is required when confidence_level='{level.value}'"
                )
        return v

    @field_validator("is_matrix_backed")
    @classmethod
    def matrix_backed_implies_high(
        cls, v: bool | None, info: ValidationInfo
    ) -> bool | None:
        if v is None:
            return v  # skip if not provided
        level = info.data.get("confidence_level")
        if v is True and level != FixConfidenceLevel.HIGH:
            raise ValueError("is_matrix_backed=True requires confidence_level='high'")
        return v

    @field_validator("confidence_score")
    @classmethod
    def score_consistent_with_level(
        cls, v: float | None, info: ValidationInfo
    ) -> float | None:
        import logging

        logger = logging.getLogger(__name__)
        level = info.data.get("confidence_level")
        if level is None or v is None:
            return v
        if level == FixConfidenceLevel.HIGH and v < 0.75:
            logger.warning(
                "confidence_score %.2f low for HIGH-level fix (expected >=0.75)", v
            )
        elif level == FixConfidenceLevel.LOW and v >= 0.40:
            logger.warning(
                "confidence_score %.2f high for LOW-level fix (expected <0.40)", v
            )
        return v

    @model_validator(mode="after")
    def score_required_if_level_set(self) -> SuggestedFix:
        if self.confidence_level is not None and self.confidence_score is None:
            raise ValueError(
                "confidence_score is required when confidence_level is set"
            )
        return self

    @model_validator(mode="after")
    def fallback_required_for_low(self) -> SuggestedFix:
        if self.confidence_level == FixConfidenceLevel.LOW:
            if (
                not self.fallback_recommendation
                or not self.fallback_recommendation.strip()
            ):
                raise ValueError(
                    "fallback_recommendation is required when confidence_level='low'"
                )
        return self


class TroubleshootRequest(BaseModel):
    diagnostic: dict[str, Any]
    verification: dict[str, Any] = Field(default_factory=dict[str, Any])
    profile: dict[str, Any] = Field(default_factory=dict[str, Any])
    profile_slug: str | None = None
    profile_name: str | None = None
    target_os: str | None = None
    python_version: str | None = None
    cuda_version: str | None = None
    session_id: uuid.UUID | None = None
    user_description: str = Field(default="", max_length=500)
    max_words: int = Field(default=500, ge=50, le=2000)
    repair_script_available: bool = False
    disclaimer: str = "AI-generated advisory. Review carefully before executing."


class TroubleshootResponse(BaseModel):
    session_id: str
    root_cause: str
    suggested_fixes: list[SuggestedFix] = Field(default_factory=list)
    repair_script_available: bool = False
    confidence: float = Field(..., ge=0.0, le=1.0)
    disclaimer: str = "AI-generated advisory. Review carefully before executing."
    suppressed_fix_count: int = 0
