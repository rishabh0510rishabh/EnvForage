"""
Tests for Issue #483 — safety_passed misused for DB persistence failure tracking.
Branch: fix/483-safety-passed-misuse
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSafetyPassedNotMisused:
    """
    Verify safety_passed=True is always set on the success audit path,
    regardless of DB persistence failure. DB failures must NOT cause
    safety_passed=False in audit logs.
    """

    @pytest.mark.asyncio
    async def test_safety_passed_true_when_persist_fails(self):
        """
        CRITICAL: Even if _persist_session raises an exception,
        safety_passed must still be True in the audit log.
        Old bug: safety_passed=not persist_failed  ← set to False on DB error.
        Fixed:   safety_passed=True  ← always True on this code path.
        """
        from app.ai.service import AITroubleshootService

        mock_provider = AsyncMock()
        mock_provider.model = "gpt-4"
        mock_provider.last_token_usage = {"total_tokens": 100,
                                          "prompt_tokens": 60,
                                          "completion_tokens": 40}
        mock_provider.complete.return_value = MagicMock(
            suggested_fixes=[],
            session_id=None,
            suppressed_fix_count=0,
            confidence=0.0,
            repair_script_available=False,
        )

        service = AITroubleshootService(provider=mock_provider)

        audit_calls = []

        async def capture_log_audit(db, *, session_id, input_hash,
                                    safety_passed, safety_violation,
                                    provider, tokens_used, latency_ms):
            audit_calls.append({
                "safety_passed": safety_passed,
                "safety_violation": safety_violation,
            })

        with patch.object(service, "_validate_response_safety"):
            with patch.object(service, "_persist_session",
                              side_effect=Exception("DB connection refused")):
                with patch.object(service, "_log_audit",
                                  side_effect=capture_log_audit):
                    with patch("app.ai.service.record_ai_token_usage"):
                        mock_db = AsyncMock()
                        mock_request = MagicMock()
                        mock_request.session_id = None
                        mock_request.user_description = "some problem"
                        mock_request.model_dump_json.return_value = "{}"

                        await service.troubleshoot(mock_request, mock_db)

        assert len(audit_calls) == 1, f"Expected 1 audit call, got {len(audit_calls)}"
        final_audit = audit_calls[0]

        assert final_audit["safety_passed"] is True, (
            f"safety_passed={final_audit['safety_passed']} but expected True. "
            "DB failure must NOT set safety_passed=False. Issue #483 NOT fixed!"
        )

    @pytest.mark.asyncio
    async def test_safety_violation_indicates_db_failure_not_safety(self):
        """
        When DB persistence fails, safety_violation field should indicate
        it's a persistence issue, not an AI safety violation.
        """
        from app.ai.service import AITroubleshootService

        mock_provider = AsyncMock()
        mock_provider.model = "gpt-4"
        mock_provider.last_token_usage = {}
        mock_provider.complete.return_value = MagicMock(
            suggested_fixes=[],
            session_id=None,
            suppressed_fix_count=0,
            confidence=0.0,
            repair_script_available=False,
        )

        service = AITroubleshootService(provider=mock_provider)
        audit_calls = []

        async def capture_log_audit(db, *, session_id, input_hash,
                                    safety_passed, safety_violation,
                                    provider, tokens_used, latency_ms):
            audit_calls.append({
                "safety_passed": safety_passed,
                "safety_violation": safety_violation,
            })

        with patch.object(service, "_validate_response_safety"):
            with patch.object(service, "_persist_session",
                              side_effect=Exception("DB down")):
                with patch.object(service, "_log_audit",
                                  side_effect=capture_log_audit):
                    with patch("app.ai.service.record_ai_token_usage"):
                        mock_db = AsyncMock()
                        mock_request = MagicMock()
                        mock_request.session_id = None
                        mock_request.user_description = "some problem"
                        mock_request.model_dump_json.return_value = "{}"

                        await service.troubleshoot(mock_request, mock_db)

        final_audit = audit_calls[0]
        # safety_violation should mention DB, not be a real safety violation
        if final_audit["safety_violation"] is not None:
            assert "DB" in final_audit["safety_violation"] or \
                   "persistence" in final_audit["safety_violation"].lower(), (
                "safety_violation must clearly indicate DB failure, not an AI safety issue"
            )

    @pytest.mark.asyncio
    async def test_safety_passed_true_and_no_violation_on_full_success(self):
        """On full success path, safety_passed=True and safety_violation=None."""
        from app.ai.service import AITroubleshootService

        mock_provider = AsyncMock()
        mock_provider.model = "gpt-4"
        mock_provider.last_token_usage = {"total_tokens": 200,
                                          "prompt_tokens": 100,
                                          "completion_tokens": 100}
        mock_provider.complete.return_value = MagicMock(
            suggested_fixes=[],
            session_id=None,
            suppressed_fix_count=0,
            confidence=0.0,
            repair_script_available=False,
        )

        service = AITroubleshootService(provider=mock_provider)
        audit_calls = []

        async def capture_log_audit(db, *, session_id, input_hash,
                                    safety_passed, safety_violation,
                                    provider, tokens_used, latency_ms):
            audit_calls.append({
                "safety_passed": safety_passed,
                "safety_violation": safety_violation,
            })

        with patch.object(service, "_validate_response_safety"):
            with patch.object(service, "_persist_session", new_callable=AsyncMock):
                with patch.object(service, "_log_audit",
                                  side_effect=capture_log_audit):
                    with patch("app.ai.service.record_ai_token_usage"):
                        mock_db = AsyncMock()
                        mock_request = MagicMock()
                        mock_request.session_id = None
                        mock_request.user_description = "some problem"
                        mock_request.model_dump_json.return_value = "{}"

                        await service.troubleshoot(mock_request, mock_db)

        final_audit = audit_calls[0]
        assert final_audit["safety_passed"] is True
        assert final_audit["safety_violation"] is None

    @pytest.mark.asyncio
    async def test_safety_passed_false_on_real_safety_violation(self):
        """Real SafetyViolationError must still set safety_passed=False."""
        from app.ai.service import AITroubleshootService
        from app.templates.safety import SafetyViolationError

        mock_provider = AsyncMock()
        mock_provider.model = "gpt-4"
        mock_provider.complete.return_value = MagicMock(suggested_fixes=[])

        service = AITroubleshootService(provider=mock_provider)
        audit_calls = []

        async def capture_log_audit(db, *, session_id, input_hash,
                                    safety_passed, safety_violation,
                                    provider, tokens_used, latency_ms):
            audit_calls.append({
                "safety_passed": safety_passed,
                "safety_violation": safety_violation,
            })

        with patch.object(service, "_validate_response_safety",
                          side_effect=SafetyViolationError(pattern="rm -rf", description="rm -rf detected")):
            with patch.object(service, "_log_audit",
                              side_effect=capture_log_audit):
                with patch("app.ai.service.record_ai_token_usage"):
                    mock_db = AsyncMock()
                    mock_request = MagicMock()
                    mock_request.session_id = None
                    mock_request.user_description = "some problem"
                    mock_request.model_dump_json.return_value = "{}"

                    with pytest.raises(SafetyViolationError):
                        await service.troubleshoot(mock_request, mock_db)

        assert audit_calls[0]["safety_passed"] is False
        assert "rm -rf" in audit_calls[0]["safety_violation"]
