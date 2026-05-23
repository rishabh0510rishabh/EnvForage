"""Troubleshoot endpoint — POST /api/v1/troubleshoot."""
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.ai.models import TroubleshootRequest
from app.ai.providers.base import LLMProviderError
from app.ai.service import AITroubleshootService
from app.api.deps import DB
from app.middleware.rate_limit import ai_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()

# Singleton service instance
_service = AITroubleshootService()


@router.post(
    "/troubleshoot",
    status_code=201,
    summary="AI-assisted environment troubleshooting (streaming)",
    description=(
        "Submit a diagnostic report and receive a streaming AI-generated "
        "root cause analysis. Returns a text/event-stream of JSON tokens."
    ),
    responses={
        201: {"description": "Streaming troubleshoot analysis started"},
        500: {"description": "Internal error"},
        503: {"description": "AI service unavailable"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def troubleshoot(
    request: TroubleshootRequest,
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
                    # Format as standard SSE
                    yield f"data: {chunk}\n\n"
            except Exception:
                logger.exception("Error in troubleshoot stream generator")
                yield "data: {\"error\": \"STREAM_ERROR\", \"message\": \"An internal error occurred while streaming analysis.\"}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable buffering for Nginx
            }
        )

    except LLMProviderError as exc:
        logger.error("LLM provider error: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "AI_SERVICE_UNAVAILABLE",
                "message": f"AI provider error: {exc.reason}",
                "provider": exc.provider,
            },
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error in troubleshoot endpoint")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred during AI analysis.",
            },
        ) from exc
