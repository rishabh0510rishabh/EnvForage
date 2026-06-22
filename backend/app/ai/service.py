"""AI Troubleshoot Service — orchestrates the full troubleshooting pipeline.

Pipeline:
    1. Build structured prompt from diagnostic context
    2. Call LLM provider for analysis
    3. Validate AI output through SafetyFilter
    4. Persist session + suggestions to DB for audit
    5. Return structured TroubleshootResponse
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import SuggestedFix, TroubleshootRequest, TroubleshootResponse
from app.ai.prompts.system import LOW_CONFIDENCE_GATE, TROUBLESHOOT_SYSTEM_PROMPT
from app.ai.prompts.troubleshoot import TroubleshootPromptBuilder
from app.ai.providers import get_provider
from app.ai.providers.base import LLMProvider, LLMProviderError
from app.middleware.metrics import record_ai_token_usage
from app.models.ai_session import AIAuditLog, AISession, AISuggestion
from app.templates.safety import SafetyViolationError, validate_rendered_output

logger = logging.getLogger(__name__)


class AITroubleshootService:
    """
    Orchestrates AI-assisted troubleshooting.

    This service is the single entry point for all AI troubleshooting
    operations. It coordinates prompt building, LLM calls, safety
    validation, database persistence, and response assembly.

    Usage::

        service = AITroubleshootService()
        response = await service.troubleshoot(request, db_session)
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._provider = provider
        self._prompt_builder = TroubleshootPromptBuilder()

    async def troubleshoot(
        self,
        request: TroubleshootRequest,
        db: AsyncSession,
    ) -> TroubleshootResponse:
        """
        Run the full AI troubleshooting pipeline.

        Args:
            request: Structured troubleshoot request with diagnostic data.
            db: Async database session for audit persistence.

        Returns:
            Try/Except structured TroubleshootResponse with root cause analysis.
        """
        session_id = str(uuid.uuid4())
        start_time = time.monotonic()
        input_hash = self._hash_input(request)

        # ── Step 1: Build prompt ──────────────────────────────────────────
        history = None
        if request.session_id:
            history = await self._fetch_session_history(db, request.session_id)

        user_message = self._prompt_builder.build(request, history=history)
        logger.info("Troubleshoot prompt built (%d chars)", len(user_message))

        # ── Step 2: Call LLM ──────────────────────────────────────────────
        provider = self._provider if self._provider is not None else get_provider()
        provider_name = type(provider).__name__
        model_name = getattr(provider, "model", "unknown")

        try:
            llm_result = await provider.complete(
                system_prompt=TROUBLESHOOT_SYSTEM_PROMPT,
                user_message=user_message,
                response_model=TroubleshootResponse,
            )
        except LLMProviderError as exc:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            record_ai_token_usage(
                provider=provider_name,
                model=model_name,
                success=False,
            )
            await self._log_audit(
                db,
                session_id=None,
                input_hash=input_hash,
                safety_passed=False,
                safety_violation=f"LLM error: {exc.reason}",
                provider=provider_name,
                tokens_used=0,
                latency_ms=latency_ms,
            )
            raise

        # ── Step 3: Safety filter ─────────────────────────────────────────
        safety_violation: str | None = None
        try:
            await self._validate_response_safety(llm_result)
        except SafetyViolationError as exc:
            safety_violation = str(exc)
            latency_ms = int((time.monotonic() - start_time) * 1000)
            record_ai_token_usage(
                provider=provider_name,
                model=model_name,
                success=False,
            )
            await self._log_audit(
                db,
                session_id=None,
                input_hash=input_hash,
                safety_passed=False,
                safety_violation=safety_violation,
                provider=provider_name,
                tokens_used=0,
                latency_ms=latency_ms,
            )
            raise

        # ── Step 4: Enrich response ───────────────────────────────────────
        llm_result.session_id = session_id
        llm_result.repair_script_available = any(
            fix.repair_template_id is not None for fix in llm_result.suggested_fixes
        )

        # ── Step 4b: Confidence gating ────────────────────────────────────
        accepted_fixes, suppressed_count = self._gate_fixes(
            llm_result.suggested_fixes, session_id
        )
        llm_result.suggested_fixes = accepted_fixes
        llm_result.suppressed_fix_count = suppressed_count
        llm_result.confidence = self._recalculate_overall_confidence(accepted_fixes)
        self._log_confidence_audit(session_id, accepted_fixes, suppressed_count)

        # ── Step 5: Persist to DB ─────────────────────────────────────────
        latency_ms = int((time.monotonic() - start_time) * 1000)
        token_usage = getattr(provider, "last_token_usage", None)

        if callable(token_usage):
            token_usage = token_usage()

        total_tokens = token_usage.get("total_tokens", 0) if token_usage else 0
        prompt_tokens = token_usage.get("prompt_tokens", 0) if token_usage else 0
        completion_tokens = (
            token_usage.get("completion_tokens", 0) if token_usage else 0
        )

        record_ai_token_usage(
            provider=provider_name,
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            success=True,
        )

        persist_failed = False
        try:
            await self._persist_session(
                db,
                session_id,
                request,
                llm_result,
                provider_name,
                model_name,
            )
        except Exception:
            persist_failed = True

        await self._log_audit(
            db,
            session_id=session_id,
            input_hash=input_hash,
            safety_passed=True,
            safety_violation="DB persistence failure" if persist_failed else None,
            provider=provider_name,
            tokens_used=total_tokens,
            latency_ms=latency_ms,
        )

        logger.info(
            "Troubleshoot complete: session=%s, fixes=%d, confidence=%.2f, latency=%dms",
            session_id,
            len(llm_result.suggested_fixes),
            llm_result.confidence,
            latency_ms,
        )

        return llm_result

    async def stream_troubleshoot(
        self,
        request: TroubleshootRequest,
        db: AsyncSession,
    ) -> AsyncIterator[str]:
        """
        Stream the AI troubleshooting response with real-time safety checks.

        Chunks are yielded immediately as they arrive from the LLM provider.
        Each chunk is checked against FORBIDDEN_PATTERNS in real-time.
        A full safety validation runs after the stream completes.
        """
        import json as _json

        from app.templates.safety import FORBIDDEN_PATTERNS

        session_id = str(uuid.uuid4())
        start_time = time.monotonic()
        input_hash = self._hash_input(request)

        history = None
        if request.session_id:
            history = await self._fetch_session_history(db, request.session_id)

        user_message = self._prompt_builder.build(request, history=history)
        provider = get_provider()
        provider_name = type(provider).__name__

        logger.info("Starting troubleshoot stream (provider=%s)", provider_name)

        import re
        compiled_patterns = [(re.compile(p, re.IGNORECASE), desc) for p, desc in FORBIDDEN_PATTERNS]

        chunks: list[str] = []
        _stream_buffer_limit = 512 * 1024  # 512 KB
        _buffer_size = 0
        safety_aborted = False

        async for chunk in provider.stream(
            system_prompt=TROUBLESHOOT_SYSTEM_PROMPT,
            user_message=user_message,
            response_model=TroubleshootResponse,
        ):
            _buffer_size += len(chunk.encode())
            if _buffer_size > _stream_buffer_limit:
                logger.warning(
                    "Stream buffer limit exceeded for session %s", session_id
                )
                yield _json.dumps({
                    "error": "STREAM_LIMIT_EXCEEDED",
                    "message": "Response too large — blocked by safety limit.",
                })
                return

            # Real-time safety: check each chunk against forbidden patterns
            for pattern, description in compiled_patterns:
                if pattern.search(chunk):
                    logger.warning(
                        "Real-time safety violation in chunk (session %s): %s",
                        session_id, description,
                    )
                    safety_aborted = True
                    yield _json.dumps({
                        "error": "SAFETY_VIOLATION",
                        "message": "Response blocked by real-time safety filter.",
                    })
                    break

            if safety_aborted:
                return

            chunks.append(chunk)
            yield chunk

        # Post-stream full safety validation
        full_response = "".join(chunks)

        try:
            llm_result = TroubleshootResponse.model_validate_json(full_response)
            await self._validate_response_safety(llm_result)
        except SafetyViolationError as exc:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            await self._log_audit(
                db,
                session_id=None,
                input_hash=input_hash,
                safety_passed=False,
                safety_violation=str(exc),
                provider=provider_name,
                tokens_used=0,
                latency_ms=latency_ms,
            )
            logger.warning("Post-stream safety violation: %s", exc)
            yield _json.dumps({
                "error": "SAFETY_VIOLATION",
                "message": "Response blocked by post-stream safety filter.",
            })
            return
        except Exception:
            logger.exception("Failed to validate streamed response")

        model_name = getattr(provider, "model", "unknown")
        persist_failed = False
        try:
            await self._persist_session(
                db,
                session_id,
                request,
                llm_result,
                provider_name,
                model_name,
            )
        except Exception:
            persist_failed = True

        latency_ms = int((time.monotonic() - start_time) * 1000)
        await self._log_audit(
            db,
            session_id=session_id,
            input_hash=input_hash,
            safety_passed=not persist_failed,
            safety_violation="DB persistence failure" if persist_failed else None,
            provider=provider_name,
            tokens_used=0,
            latency_ms=latency_ms,
        )

    async def _fetch_session_history(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> list[AISuggestion]:
        """Fetch previous AI suggestions for a given session ID."""
        try:
            stmt = (
                select(AISuggestion)
                .where(AISuggestion.session_id == session_id)
                .order_by(AISuggestion.step_number.asc())
            )
            result = await db.execute(stmt)
            return list(result.scalars().all())

        except OperationalError as exc:
            logger.critical(
                "Critical database connectivity failure for session %s: %s",
                session_id,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database service is temporarily unavailable. Unable to process history request.",
            )
        except SQLAlchemyError as exc:
            logger.error(
                "Transient database error fetching session history for %s: %s",
                session_id,
                exc,
            )
            return []

    # ── Private helpers ───────────────────────────────────────────────────

    def _hash_input(self, request: TroubleshootRequest) -> str:
        """Create a SHA-256 hash of the input for audit logging (no PII)."""
        raw = request.model_dump_json()
        return hashlib.sha256(raw.encode()).hexdigest()[:64]

    async def _validate_response_safety(self, response: TroubleshootResponse) -> None:
        """Run all text fields through the template SafetyFilter."""
        await validate_rendered_output(response.root_cause, "ai_root_cause")

        for fix in response.suggested_fixes:
            await validate_rendered_output(fix.title, "ai_fix_title")
            await validate_rendered_output(fix.description, "ai_fix_description")
            for cmd in fix.safe_commands:
                await validate_rendered_output(cmd, "ai_safe_command")

    async def _persist_session(
        self,
        db: AsyncSession,
        session_id: str,
        request: TroubleshootRequest,
        response: TroubleshootResponse,
        provider_name: str,
        model_name: str,
    ) -> None:
        """Persist the AI session and suggestions to the database."""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                db_session = AISession(
                    id=uuid.UUID(session_id),
                    provider=provider_name,
                    model=model_name,
                    created_at=datetime.now(UTC),
                )

                db.add(db_session)
                await db.flush()

                for fix in response.suggested_fixes:
                    db_suggestion = AISuggestion(
                        id=uuid.uuid4(),
                        session_id=db_session.id,
                        step_number=fix.step,
                        title=fix.title,
                        description=fix.description,
                        severity=fix.severity,
                        safe_commands=fix.safe_commands if fix.safe_commands else None,
                        template_id=fix.repair_template_id,
                        created_at=datetime.now(UTC),
                    )
                    db.add(db_suggestion)
                return

            except Exception as exc:
                await db.rollback()
                logger.exception(
                    "Failed to persist AI session (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries,
                    exc,
                )

                if attempt < max_retries - 1:
                    logger.warning(
                        "Retrying AI session persistencefor session %s",
                        session_id,
                    )
                    await asyncio.sleep(1)
                else:
                    logger.critical(
                        "AI session persistence permanently failed for session %s",
                        session_id,
                    )
                    raise

        logger.critical(
            "AI session persistence permanently failed for session %s",
            session_id,
        )

    async def _log_audit(
        self,
        db: AsyncSession,
        *,
        session_id: str | None,
        input_hash: str,
        safety_passed: bool,
        safety_violation: str | None,
        provider: str,
        tokens_used: int,
        latency_ms: int,
    ) -> None:
        """Write an audit log entry for the AI interaction."""
        try:
            log = AIAuditLog(
                id=uuid.uuid4(),
                session_id=uuid.UUID(session_id) if session_id else None,
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
            logger.exception("Failed to write audit log to database: %s", exc)

    # confidence gating

    def _gate_fixes(
        self, fixes: list[SuggestedFix], session_id: str
    ) -> tuple[list[SuggestedFix], int]:
        """Suppress fixes whose confidence_score is below LOW_CONFIDENCE_GATE."""
        accepted, suppressed = [], 0
        for fix in fixes:
            if (fix.confidence_score or 0.0) < LOW_CONFIDENCE_GATE:
                logger.warning(
                    "session=%s step=%d '%s' suppressed (score=%.2f < gate=%.2f)",
                    session_id,
                    fix.step,
                    fix.title,
                    fix.confidence_score or 0.0,
                    LOW_CONFIDENCE_GATE,
                )
                suppressed += 1
            else:
                accepted.append(fix)
        return accepted, suppressed

    # Overall confidence recalculation

    def _recalculate_overall_confidence(self, fixes: list[SuggestedFix]) -> float:
        """
        Weighted average of per-fix scores.
        CRITICAL=3×, WARNING=2×, INFO=1× weight.
        Returns 0.0 if no fixes present.
        """
        if not fixes:
            return 0.0
        weight_map = {"CRITICAL": 3.0, "WARNING": 2.0, "INFO": 1.0}
        total_w, weighted_sum = 0.0, 0.0
        for fix in fixes:
            w = weight_map.get(fix.severity, 1.0)
            weighted_sum += (fix.confidence_score or 0.0) * w
            total_w += w
        return round(weighted_sum / total_w, 4)

    # Audit logging

    def _log_confidence_audit(
        self, session_id: str, fixes: list[SuggestedFix], suppressed: int
    ) -> None:
        for fix in fixes:
            logger.info(
                "CONFIDENCE_AUDIT session=%s step=%d level=%s score=%.2f matrix_backed=%s severity=%s",
                session_id,
                fix.step,
                fix.confidence_level.value if fix.confidence_level else "unknown",
                fix.confidence_score or 0.0,
                fix.is_matrix_backed,
                fix.severity,
            )
        if suppressed:
            logger.info(
                "CONFIDENCE_AUDIT session=%s suppressed_fixes=%d",
                session_id,
                suppressed,
            )

    # Prompt builder

    def _build_user_message(self, request: TroubleshootRequest) -> str:
        parts = [
            "## Diagnostic Report",
            json.dumps(request.diagnostic, indent=2),
            "",
            "## Verification Results",
            json.dumps(request.verification, indent=2),
            "",
            "## Environment Profile",
            json.dumps(request.profile, indent=2),
        ]
        if request.user_description.strip():
            parts += ["", "## User Description", request.user_description.strip()]
        parts += [
            "",
            "## Instructions",
            f"Return a TroubleshootResponse JSON. Max {request.max_words} words. "
            "Populate confidence_level, confidence_score, is_matrix_backed, "
            "uncertainty_reason, and fallback_recommendation for EVERY SuggestedFix.",
        ]
        return "\n".join(parts)
