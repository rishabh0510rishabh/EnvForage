"""
Additional integration-level tests for service.py
covering confidence gating, retry logic, audit log paths, and stream path.
Run these before committing any of the 3 fix branches.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.service import AITroubleshootService


class TestConfidenceGating:
    """Tests for _gate_fixes and _recalculate_overall_confidence."""

    def test_gate_fixes_suppresses_low_confidence(self):
        service = AITroubleshootService()
        fixes = [
            MagicMock(confidence_score=0.9, step=1, title="Fix A", severity="CRITICAL"),
            MagicMock(confidence_score=0.1, step=2, title="Fix B", severity="WARNING"),  # below gate
            MagicMock(confidence_score=0.8, step=3, title="Fix C", severity="INFO"),
        ]
        accepted, suppressed = service._gate_fixes(fixes, "test-session")
        assert len(accepted) == 2
        assert suppressed == 1
        assert fixes[1] not in accepted

    def test_gate_fixes_none_confidence_treated_as_zero(self):
        service = AITroubleshootService()
        fix = MagicMock(confidence_score=None, step=1, title="Fix", severity="INFO")
        accepted, suppressed = service._gate_fixes([fix], "test-session")
        # None treated as 0.0, below LOW_CONFIDENCE_GATE
        assert suppressed == 1

    def test_recalculate_confidence_empty_list(self):
        service = AITroubleshootService()
        assert service._recalculate_overall_confidence([]) == 0.0

    def test_recalculate_confidence_weighted(self):
        service = AITroubleshootService()
        fixes = [
            MagicMock(confidence_score=1.0, severity="CRITICAL"),  # weight 3
            MagicMock(confidence_score=0.0, severity="INFO"),       # weight 1
        ]
        result = service._recalculate_overall_confidence(fixes)
        # (1.0*3 + 0.0*1) / (3+1) = 0.75
        assert result == 0.75


class TestPersistSessionRetryLogic:
    """Tests for retry logic in _persist_session."""

    @pytest.mark.asyncio
    async def test_retries_three_times_on_failure(self):
        service = AITroubleshootService()
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.rollback = AsyncMock()

        with patch("app.ai.service.AISession") as mock_session:
            mock_session.side_effect = Exception("DB error")

            with patch("app.ai.service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                with pytest.raises(Exception):
                    await service._persist_session(
                        mock_db,
                        "12345678-1234-5678-1234-567812345678",
                        MagicMock(),
                        MagicMock(suggested_fixes=[]),
                        "OpenAI",
                        "gpt-4",
                    )
                # Should sleep between retries (max_retries-1 = 2 times)
                assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_succeeds_on_second_attempt(self):
        service = AITroubleshootService()
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.rollback = AsyncMock()

        call_count = 0

        with patch("app.ai.service.AISession") as mock_session:
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("transient error")
                return MagicMock(id="session-uuid")

            mock_session.side_effect = side_effect

            with patch("app.ai.service.asyncio.sleep", new_callable=AsyncMock):
                with patch("app.ai.service.AISuggestion"):
                    await service._persist_session(
                        mock_db,
                        "12345678-1234-5678-1234-567812345678",
                        MagicMock(),
                        MagicMock(suggested_fixes=[]),
                        "OpenAI",
                        "gpt-4",
                    )
            assert call_count == 2  # failed once, succeeded on retry


class TestAuditLogPaths:
    """Verify _log_audit is called correctly on all code paths."""

    @pytest.mark.asyncio
    async def test_audit_log_written_on_llm_error(self):
        from app.ai.providers.base import LLMProviderError
        mock_provider = AsyncMock()
        mock_provider.model = "gpt-4"
        mock_provider.complete.side_effect = LLMProviderError(provider="MockProvider", reason="timeout")

        service = AITroubleshootService(provider=mock_provider)
        audit_calls = []

        async def capture(*args, **kwargs):
            audit_calls.append(kwargs)

        with patch.object(service, "_log_audit", side_effect=capture):
            with patch("app.ai.service.record_ai_token_usage"):
                mock_db = AsyncMock()
                mock_request = MagicMock()
                mock_request.session_id = None
                mock_request.user_description = "some problem"
                mock_request.model_dump_json.return_value = "{}"

                with pytest.raises(LLMProviderError):
                    await service.troubleshoot(mock_request, mock_db)

        assert len(audit_calls) == 1
        assert audit_calls[0]["safety_passed"] is False
        assert audit_calls[0]["session_id"] is None
        assert "LLM error" in audit_calls[0]["safety_violation"]

    @pytest.mark.asyncio
    async def test_audit_log_session_id_set_on_success(self):
        mock_provider = AsyncMock()
        mock_provider.model = "gpt-4"
        mock_provider.last_token_usage = {}
        mock_provider.complete.return_value = MagicMock(
            suggested_fixes=[], session_id=None,
            suppressed_fix_count=0, confidence=0.0,
            repair_script_available=False,
        )
        service = AITroubleshootService(provider=mock_provider)
        audit_calls = []

        async def capture(*args, **kwargs):
            audit_calls.append(kwargs)

        with patch.object(service, "_validate_response_safety"):
            with patch.object(service, "_persist_session", new_callable=AsyncMock):
                with patch.object(service, "_log_audit", side_effect=capture):
                    with patch("app.ai.service.record_ai_token_usage"):
                        mock_db = AsyncMock()
                        mock_request = MagicMock()
                        mock_request.session_id = None
                        mock_request.user_description = "some problem"
                        mock_request.model_dump_json.return_value = "{}"

                        await service.troubleshoot(mock_request, mock_db)

        assert len(audit_calls) == 1
        assert audit_calls[0]["session_id"] is not None  # UUID set on success


class TestHashInput:
    """Tests for _hash_input determinism and length."""

    def test_hash_is_64_chars(self):
        service = AITroubleshootService()
        mock_request = MagicMock()
        mock_request.model_dump_json.return_value = '{"key": "value"}'
        result = service._hash_input(mock_request)
        assert len(result) == 64

    def test_hash_is_deterministic(self):
        service = AITroubleshootService()
        mock_request = MagicMock()
        mock_request.model_dump_json.return_value = '{"key": "value"}'
        assert service._hash_input(mock_request) == service._hash_input(mock_request)

    def test_different_inputs_give_different_hashes(self):
        service = AITroubleshootService()
        r1 = MagicMock()
        r1.model_dump_json.return_value = '{"key": "a"}'
        r2 = MagicMock()
        r2.model_dump_json.return_value = '{"key": "b"}'
        assert service._hash_input(r1) != service._hash_input(r2)
