"""Tests for AI Pydantic models."""

import uuid

import pytest
from pydantic import ValidationError

from app.ai.models import (
    LLMResponseMeta,
    SuggestedFix,
    TroubleshootRequest,
    TroubleshootResponse,
)


class TestTroubleshootRequest:
    def test_minimal_request(self):
        req = TroubleshootRequest(diagnostic={"os": {"name": "Ubuntu"}})
        assert req.diagnostic["os"]["name"] == "Ubuntu"
        assert req.profile_slug is None
        assert req.user_description == ""

    def test_full_request(self):
        req = TroubleshootRequest(
            diagnostic={"os": {"name": "Ubuntu"}},
            profile_slug="pytorch-cuda",
            profile_name="PyTorch + CUDA",
            target_os="LINUX",
            python_version="3.11",
            cuda_version="12.1",
            user_description="CUDA not working",
        )
        assert req.profile_slug == "pytorch-cuda"
        assert req.cuda_version == "12.1"

    def test_session_id_is_validated_as_uuid(self):
        req = TroubleshootRequest(
            diagnostic={"os": {"name": "Ubuntu"}},
            session_id="550e8400-e29b-41d4-a716-446655440000",
        )
        assert req.session_id == uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_session_id_rejects_invalid_uuid(self):
        with pytest.raises(ValidationError):
            TroubleshootRequest(
                diagnostic={"os": {"name": "Ubuntu"}},
                session_id="invalid-uuid",
            )

    def test_user_description_max_length(self):
        with pytest.raises(ValidationError):
            TroubleshootRequest(
                diagnostic={"os": {}},
                user_description="X" * 501,
            )

    def test_user_description_at_max_length(self):
        req = TroubleshootRequest(
            diagnostic={"os": {}},
            user_description="X" * 500,
        )
        assert len(req.user_description) == 500


class TestSuggestedFix:
    def test_valid_fix(self):
        fix = SuggestedFix(
            step=1,
            title="Upgrade CUDA",
            description="Your CUDA version is outdated.",
            severity="CRITICAL",
            safe_commands=["nvcc --version"],
            repair_template_id="repair_cuda_upgrade",
        )
        assert fix.step == 1
        assert fix.severity == "CRITICAL"

    def test_invalid_severity(self):
        with pytest.raises(ValidationError):
            SuggestedFix(
                step=1,
                title="Test",
                description="Test",
                severity="FATAL",
            )

    def test_default_safe_commands(self):
        fix = SuggestedFix(step=1, title="Test", description="D", severity="INFO")
        assert fix.safe_commands == []
        assert fix.repair_template_id is None


class TestTroubleshootResponse:
    def test_valid_response(self):
        resp = TroubleshootResponse(
            session_id="abc-123",
            root_cause="CUDA version mismatch",
            suggested_fixes=[],
            confidence=0.85,
        )
        assert resp.session_id == "abc-123"
        assert resp.confidence == 0.85
        assert "advisory" in resp.disclaimer.lower()

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            TroubleshootResponse(
                session_id="x",
                root_cause="y",
                suggested_fixes=[],
                confidence=1.5,
            )

    def test_confidence_lower_bound(self):
        with pytest.raises(ValidationError):
            TroubleshootResponse(
                session_id="x",
                root_cause="y",
                suggested_fixes=[],
                confidence=-0.1,
            )


class TestLLMResponseMeta:
    def test_defaults(self):
        meta = LLMResponseMeta(provider="openrouter", model="gpt-4o")
        assert meta.prompt_tokens == 0
        assert meta.total_tokens == 0

    def test_with_tokens(self):
        meta = LLMResponseMeta(
            provider="openrouter",
            model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        assert meta.total_tokens == 150


class TestFixConfidenceLevel:
    def test_high_confidence_valid(self):
        fix = SuggestedFix(
            step=1,
            title="Upgrade CUDA",
            description="CUDA mismatch.",
            severity="CRITICAL",
            safe_commands=["nvcc --version"],
            confidence_level="high",
            confidence_score=0.90,
            is_matrix_backed=True,
            uncertainty_reason=None,
        )
        assert fix.confidence_level.value == "high"
        assert fix.is_matrix_backed is True

    def test_medium_requires_uncertainty_reason(self):
        with pytest.raises(ValidationError, match="uncertainty_reason is required"):
            SuggestedFix(
                step=1,
                title="Check driver",
                description="Driver may be outdated.",
                severity="WARNING",
                confidence_level="medium",
                confidence_score=0.60,
                is_matrix_backed=False,
                uncertainty_reason=None,
            )

    def test_low_requires_uncertainty_reason(self):
        with pytest.raises(ValidationError, match="uncertainty_reason is required"):
            SuggestedFix(
                step=1,
                title="Rebuild Python",
                description="Edge case fix.",
                severity="INFO",
                confidence_level="low",
                confidence_score=0.25,
                is_matrix_backed=False,
                uncertainty_reason="",
            )

    def test_medium_with_reason_valid(self):
        fix = SuggestedFix(
            step=1,
            title="Check driver",
            description="Driver may be outdated.",
            severity="WARNING",
            confidence_level="medium",
            confidence_score=0.60,
            is_matrix_backed=False,
            uncertainty_reason="Exact GPU model not in diagnostic report.",
        )
        assert fix.confidence_level.value == "medium"

    def test_low_with_reason_and_fallback_valid(self):
        fix = SuggestedFix(
            step=1,
            title="Try WSL2",
            description="May be more stable.",
            severity="INFO",
            confidence_level="low",
            confidence_score=0.25,
            is_matrix_backed=False,
            uncertainty_reason="No direct evidence in report.",
            fallback_recommendation="Contact support team.",
        )
        assert fix.confidence_level.value == "low"

    def test_matrix_backed_true_requires_high(self):
        with pytest.raises(ValidationError, match="requires confidence_level='high'"):
            SuggestedFix(
                step=1,
                title="Fix",
                description="Fix.",
                severity="WARNING",
                confidence_level="medium",
                confidence_score=0.60,
                is_matrix_backed=True,
                uncertainty_reason="some reason",
            )

    def test_matrix_backed_false_with_high_valid(self):
        fix = SuggestedFix(
            step=1,
            title="Upgrade CUDA",
            description="CUDA mismatch.",
            severity="CRITICAL",
            confidence_level="high",
            confidence_score=0.80,
            is_matrix_backed=False,
        )
        assert fix.is_matrix_backed is False

    def test_confidence_score_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            SuggestedFix(
                step=1,
                title="Fix",
                description="Fix.",
                severity="INFO",
                confidence_level="low",
                confidence_score=-0.01,
                is_matrix_backed=False,
                uncertainty_reason="No data.",
            )

    def test_confidence_score_above_one_rejected(self):
        with pytest.raises(ValidationError):
            SuggestedFix(
                step=1,
                title="Fix",
                description="Fix.",
                severity="INFO",
                confidence_level="high",
                confidence_score=1.01,
                is_matrix_backed=False,
            )
