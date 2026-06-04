"""
Tests for Issue #481 — record_ai_token_usage called but not imported.
Branch: fix/481-record-ai-token-usage-import
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRecordAITokenUsageImport:
    """Verify record_ai_token_usage is importable and called correctly."""

    def test_import_exists(self):
        """record_ai_token_usage must be importable from app.middleware.metrics."""
        try:
            from app.middleware.metrics import record_ai_token_usage
            assert callable(record_ai_token_usage)
        except ImportError:
            pytest.fail(
                "record_ai_token_usage is NOT importable from app.middleware.metrics. "
                "Issue #481 is NOT fixed."
            )

    def test_service_imports_function(self):
        """service.py must import record_ai_token_usage at module level."""
        try:
            import app.ai.service as service_module
            assert hasattr(service_module, "record_ai_token_usage"), (
                "record_ai_token_usage not found in service module namespace. "
                "Add: from app.middleware.metrics import record_ai_token_usage"
            )
        except ImportError as e:
            pytest.fail(f"Could not import service module: {e}")

    @pytest.mark.asyncio
    async def test_token_usage_called_on_llm_error(self):
        """record_ai_token_usage must be called with success=False on LLM error."""
        from app.ai.providers.base import LLMProviderError
        from app.ai.service import AITroubleshootService

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = LLMProviderError(provider="MockProvider", reason="timeout")
        mock_provider.model = "gpt-4"

        service = AITroubleshootService(provider=mock_provider)
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.session_id = None
        mock_request.user_description = "some problem"
        mock_request.model_dump_json.return_value = "{}"

        with patch("app.ai.service.record_ai_token_usage") as mock_record:
            with pytest.raises(LLMProviderError):
                await service.troubleshoot(mock_request, mock_db)

            mock_record.assert_called_once_with(
                provider=type(mock_provider).__name__,
                model="gpt-4",
                success=False,
            )

    @pytest.mark.asyncio
    async def test_token_usage_called_on_safety_violation(self):
        """record_ai_token_usage must be called with success=False on SafetyViolationError."""
        from app.ai.service import AITroubleshootService
        from app.templates.safety import SafetyViolationError

        mock_provider = AsyncMock()
        mock_provider.model = "gpt-4"
        mock_provider.complete.return_value = MagicMock(
            suggested_fixes=[], session_id=None
        )

        service = AITroubleshootService(provider=mock_provider)

        with patch.object(service, "_validate_response_safety",
                          side_effect=SafetyViolationError(pattern="unsafe", description="unsafe content")):
            with patch("app.ai.service.record_ai_token_usage") as mock_record:
                mock_db = AsyncMock()
                mock_request = MagicMock()
                mock_request.session_id = None
                mock_request.user_description = "some problem"
                mock_request.model_dump_json.return_value = "{}"

                with pytest.raises(SafetyViolationError):
                    await service.troubleshoot(mock_request, mock_db)

                mock_record.assert_called_once_with(
                    provider=type(mock_provider).__name__,
                    model="gpt-4",
                    success=False,
                )

    @pytest.mark.asyncio
    async def test_token_usage_called_on_success(self):
        """record_ai_token_usage must be called with success=True on happy path."""
        from app.ai.service import AITroubleshootService

        mock_provider = AsyncMock()
        mock_provider.model = "gpt-4"
        mock_provider.last_token_usage = {"total_tokens": 500,
                                          "prompt_tokens": 300,
                                          "completion_tokens": 200}
        mock_provider.complete.return_value = MagicMock(
            suggested_fixes=[], session_id=None,
            suppressed_fix_count=0, confidence=0.0,
            repair_script_available=False
        )

        service = AITroubleshootService(provider=mock_provider)

        with patch.object(service, "_validate_response_safety"):
            with patch.object(service, "_persist_session", new_callable=AsyncMock):
                with patch.object(service, "_log_audit", new_callable=AsyncMock):
                    with patch("app.ai.service.record_ai_token_usage") as mock_record:
                        mock_db = AsyncMock()
                        mock_request = MagicMock()
                        mock_request.session_id = None
                        mock_request.user_description = "some problem"
                        mock_request.model_dump_json.return_value = "{}"

                        await service.troubleshoot(mock_request, mock_db)

                        # Last call should be success=True
                        last_call = mock_record.call_args_list[-1]
                        assert last_call.kwargs.get("success") is True
