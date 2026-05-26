"""Troubleshoot endpoint — POST /api/v1/troubleshoot."""

from collections.abc import AsyncIterator

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.ai.models import TroubleshootRequest
from app.ai.providers.base import LLMProviderError
from app.ai.service import AITroubleshootService
from app.api.deps import DB
from app.core.exceptions import AIServiceUnavailableError, InternalServerError
from app.middleware.rate_limit import ai_rate_limit

logger = structlog.get_logger(__name__)
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
)
async def troubleshoot(
    request: TroubleshootRequest,
    db: DB,
    _rate_limit: None = Depends(ai_rate_limit),
) -> StreamingResponse:

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for chunk in _service.stream_troubleshoot(request, db):
                yield f"data: {chunk}\n\n"
        except Exception:
            logger.exception(
                "troubleshoot_stream_error",
                event="stream_generator_failed",
            )
            yield (
                'data: {"error":"STREAM_ERROR","message":"Internal streaming error."}\n\n'
            )

    try:
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except LLMProviderError as exc:
        logger.error(
            "llm_provider_error",
            provider=getattr(exc, "provider", None),
            reason=getattr(exc, "reason", str(exc)),
        )
        raise AIServiceUnavailableError(
            provider=getattr(exc, "provider", None),
            reason=getattr(exc, "reason", str(exc)),
        ) from exc

    except Exception as exc:
        logger.exception(
            "unexpected_troubleshoot_error",
            error=str(exc),
        )
        raise InternalServerError(
            "An unexpected error occurred during AI analysis."
        ) from exc