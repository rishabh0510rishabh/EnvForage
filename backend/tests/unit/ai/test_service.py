"""Unit tests for AITroubleshootService confidence gating."""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.ai.models import FixConfidenceLevel, TroubleshootRequest
from app.ai.prompts.system import LOW_CONFIDENCE_GATE
from app.ai.providers.mock import MockProvider
from app.ai.service import AITroubleshootService


def _dummy_request():
    return TroubleshootRequest(
        diagnostic={
            "os": {"name": "Windows 11", "architecture": "x86_64", "version": "11.0"},
            "cpu": {"brand": "Intel i7", "cores": 8, "threads": 16},
            "ram": {"total_gb": 16, "available_gb": 8},
            "gpus": [{"name": "RTX 3080", "vram_gb": 10, "driver_version": "520.0"}],
            "cuda": {
                "version": "11.7",
                "toolkit_path": "C:/CUDA",
                "cudnn_version": None,
                "nccl_version": None,
            },
            "python_installations": [],
            "active_python": {
                "path": "C:/Python311",
                "pip_version": "23.0",
                "is_venv": False,
                "venv_path": None,
            },
            "agent_version": "1.0.0",
        },
        verification={"torch_cuda": False, "nvcc": True},
        profile={"framework": "pytorch", "version": "2.1.0"},
        user_description="torch.cuda.is_available() returns False",
    )


def _mock_db():
    db = AsyncMock()
    db.add = Mock()
    return db


async def _call(scenario):
    mock_provider = MockProvider(scenario=scenario)
    with patch("app.ai.service.get_provider", return_value=mock_provider):
        service = AITroubleshootService()
        return await service.troubleshoot(_dummy_request(), db=_mock_db())


@pytest.mark.asyncio
async def test_gate_suppresses_below_threshold():
    response = await _call("gate")
    assert response.suppressed_fix_count == 1
    assert len(response.suggested_fixes) == 0


@pytest.mark.asyncio
async def test_gate_passes_above_threshold():
    response = await _call("high")
    assert response.suppressed_fix_count == 0
    assert len(response.suggested_fixes) == 2
    for fix in response.suggested_fixes:
        assert fix.confidence_score >= LOW_CONFIDENCE_GATE


@pytest.mark.asyncio
async def test_mixed_scenario_partial_pass():
    response = await _call("mixed")
    assert response.suppressed_fix_count == 0
    assert len(response.suggested_fixes) == 3


@pytest.mark.asyncio
async def test_overall_confidence_weighted_average():
    response = await _call("mixed")
    expected = round((0.91 * 3 + 0.58 * 2 + 0.32 * 1) / 6, 4)
    assert abs(response.confidence - expected) < 0.001


@pytest.mark.asyncio
async def test_overall_confidence_zero_when_no_fixes():
    response = await _call("gate")
    assert response.confidence == 0.0


@pytest.mark.asyncio
async def test_session_id_is_uuid():
    mock_provider = MockProvider(scenario="high")
    with patch("app.ai.service.get_provider", return_value=mock_provider):
        service = AITroubleshootService()
        r1 = await service.troubleshoot(_dummy_request(), db=_mock_db())
        r2 = await service.troubleshoot(_dummy_request(), db=_mock_db())
    uuid.UUID(r1.session_id)
    uuid.UUID(r2.session_id)
    assert r1.session_id != r2.session_id


@pytest.mark.asyncio
async def test_all_accepted_fixes_have_confidence_fields():
    response = await _call("mixed")
    for fix in response.suggested_fixes:
        assert fix.confidence_level in FixConfidenceLevel
        assert 0.0 <= fix.confidence_score <= 1.0
        assert isinstance(fix.is_matrix_backed, bool)
        if fix.confidence_level in (FixConfidenceLevel.MEDIUM, FixConfidenceLevel.LOW):
            assert fix.uncertainty_reason and fix.uncertainty_reason.strip()


@pytest.mark.asyncio
async def test_suppressed_count_in_response():
    response = await _call("gate")
    assert response.suppressed_fix_count == 1
