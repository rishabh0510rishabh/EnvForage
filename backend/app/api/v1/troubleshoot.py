"""Troubleshoot endpoint — POST /api/v1/troubleshoot."""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.ai.models import TroubleshootRequest
from app.ai.providers.base import LLMProviderError
from app.ai.service import AITroubleshootService
from app.api.deps import DB
from app.core.exceptions import AIServiceUnavailableError, InternalServerError
from app.middleware.rate_limit import ai_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()

_service = AITroubleshootService()


@router.post(
    "/troubleshoot",
    status_code=201,
    summary="AI-assisted environment troubleshooting (streaming)",
    description=(
        "Submit a diagnostic report and receive a streaming AI-generated "
        "root cause analysis. Returns a text/event-stream of JSON tokens."
    ),
    tags=["AI"],
    responses={
        201: {"description": "Streaming troubleshoot analysis started"},
        500: {"description": "Internal error"},
        503: {"description": "AI provider unavailable or timed out"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def troubleshoot(
    request: TroubleshootRequest,
    http_request: Request,
    db: DB,
    _rate_limit: None = Depends(ai_rate_limit),
) -> StreamingResponse:
    """
    Accept a structured diagnostic report and return a stream of AI-powered
    troubleshooting tokens via Server-Sent Events (SSE).
    """
    try:

        async def event_generator() -> AsyncIterator[str]:
            try:
                async for chunk in _service.stream_troubleshoot(request, db):
                    yield f"data: {chunk}\n\n"
            except LLMProviderError as exc:
                logger.error("LLM provider error in stream: %s", exc)
                error_payload = json.dumps(
                    {"error": "PROVIDER_ERROR", "message": str(exc.reason)}
                )
                yield f"data: {error_payload}\n\n"
            except Exception:
                logger.exception("Error in troubleshoot stream generator")
                error_payload = json.dumps(
                    {"error": "STREAM_ERROR", "message": "Internal streaming error."}
                )
                yield f"data: {error_payload}\n\n"

        stream: AsyncIterator[str] = event_generator()
        tracker = getattr(http_request.app.state, "stream_tracker", None)
        if tracker is not None:
            stream = tracker.track(stream)

        return StreamingResponse(
            stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except LLMProviderError as exc:
        logger.error("LLM provider error: %s", exc)
        raise AIServiceUnavailableError(
            provider=getattr(exc, "provider", None),
            reason=getattr(exc, "reason", str(exc)),
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error in troubleshoot endpoint")
        raise InternalServerError(
            "An unexpected error occurred during AI analysis."
        ) from exc
