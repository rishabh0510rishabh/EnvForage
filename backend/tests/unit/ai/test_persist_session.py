# Unit tests for _persist_session bug fix (Issue #300).
#
# Verifies that:
# 1. A DB constraint error is logged with full traceback (logger.exception).
# 2. db.rollback() is called when persistence fails.
# 3. The exception is re-raised so the caller can react.
# 4. troubleshoot() marks the audit log as safety_passed=True with
#    safety_violation="DB persistence failure" when _persist_session raises.

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.service import AITroubleshootService

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_mock_db():
    """Return a mock AsyncSession with all async methods pre-configured."""
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    return db


def _make_request():
    """Return a minimal TroubleshootRequest-like mock."""
    req = MagicMock()
    req.session_id = None
    req.model_dump_json.return_value = '{"env":"test"}'
    return req


def _make_llm_result():
    """Return a minimal TroubleshootResponse-like mock."""
    result = MagicMock()
    result.suggested_fixes = []
    result.confidence = 0.9
    result.session_id = None
    result.repair_script_available = False
    return result


# ── Tests for _persist_session ────────────────────────────────────────────────
async def test_persist_session_calls_rollback_on_db_error():
    """db.rollback() must be awaited when a DB error occurs during flush."""
    service = AITroubleshootService()
    db = _make_mock_db()

    # Simulate a DB constraint error on flush (e.g. ForeignKeyViolation)
    db.flush.side_effect = Exception("FOREIGN KEY constraint failed")

    with pytest.raises(Exception, match="FOREIGN KEY constraint failed"):
        await service._persist_session(
            db,
            session_id=str(uuid.uuid4()),
            request=_make_request(),
            response=_make_llm_result(),
            provider_name="TestProvider",
            model_name="test-model",
        )

    assert db.rollback.call_count == 3
async def test_persist_session_reraises_exception():
    """_persist_session must re-raise the DB exception after logging."""
    service = AITroubleshootService()
    db = _make_mock_db()
    db.flush.side_effect = Exception("duplicate key value violates unique constraint")

    with pytest.raises(Exception, match="duplicate key value"):
        await service._persist_session(
            db,
            session_id=str(uuid.uuid4()),
            request=_make_request(),
            response=_make_llm_result(),
            provider_name="TestProvider",
            model_name="test-model",
        )
async def test_persist_session_logs_full_traceback_on_error():
    """logger.exception must be called (not logger.error) so traceback is captured."""
    service = AITroubleshootService()
    db = _make_mock_db()
    db.flush.side_effect = Exception("constraint violation")

    with patch("app.ai.service.logger") as mock_logger:
        with pytest.raises(Exception):
            await service._persist_session(
                db,
                session_id=str(uuid.uuid4()),
                request=_make_request(),
                response=_make_llm_result(),
                provider_name="TestProvider",
                model_name="test-model",
            )

        # logger.exception includes exc_info=True automatically
        assert mock_logger.exception.call_count == 3
        # logger.error must NOT be used (it drops the traceback)
        mock_logger.error.assert_not_called()


# ── Tests for troubleshoot() audit propagation ────────────────────────────────
async def test_troubleshoot_audit_marked_failed_when_persist_fails():
    """When _persist_session raises, _log_audit must be called with safety_passed=True."""
    service = AITroubleshootService()

    llm_result = _make_llm_result()

    with (
        patch.object(service, "_fetch_session_history", new=AsyncMock(return_value=[])),
        patch.object(service._prompt_builder, "build", return_value="prompt"),
        patch("app.ai.service.get_provider") as mock_get_provider,
        patch.object(
            service,
            "_persist_session",
            new=AsyncMock(side_effect=Exception("DB constraint error")),
        ),
        patch.object(service, "_log_audit", new=AsyncMock()) as mock_log_audit,
        patch.object(service, "_validate_response_safety", return_value=None),
    ):
        mock_provider = MagicMock()
        mock_provider.complete = AsyncMock(return_value=llm_result)
        mock_provider.__class__.__name__ = "MockProvider"
        mock_provider.last_token_usage = MagicMock(
            return_value={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )
        mock_get_provider.return_value = mock_provider

        request = _make_request()
        db = _make_mock_db()

        # The response should still be returned (user experience not broken)
        result = await service.troubleshoot(request, db)
        assert result is llm_result

        # Audit MUST record the failure
        mock_log_audit.assert_awaited_once()
        call_kwargs = mock_log_audit.call_args.kwargs
        assert call_kwargs["safety_passed"] is True
        assert call_kwargs["safety_violation"] == "DB persistence failure"
async def test_troubleshoot_audit_marked_passed_when_persist_succeeds():
    """When _persist_session succeeds, _log_audit must be called with safety_passed=True."""
    service = AITroubleshootService()

    llm_result = _make_llm_result()

    with (
        patch.object(service, "_fetch_session_history", new=AsyncMock(return_value=[])),
        patch.object(service._prompt_builder, "build", return_value="prompt"),
        patch("app.ai.service.get_provider") as mock_get_provider,
        patch.object(service, "_persist_session", new=AsyncMock()),
        patch.object(service, "_log_audit", new=AsyncMock()) as mock_log_audit,
        patch.object(service, "_validate_response_safety", return_value=None),
    ):
        mock_provider = MagicMock()
        mock_provider.complete = AsyncMock(return_value=llm_result)
        mock_provider.__class__.__name__ = "MockProvider"
        mock_provider.last_token_usage = MagicMock(
            return_value={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )
        mock_get_provider.return_value = mock_provider

        request = _make_request()
        db = _make_mock_db()

        await service.troubleshoot(request, db)

        call_kwargs = mock_log_audit.call_args.kwargs
        assert call_kwargs["safety_passed"] is True
        assert call_kwargs["safety_violation"] is None
