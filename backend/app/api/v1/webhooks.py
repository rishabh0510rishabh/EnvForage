from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB, require_admin
from app.config import get_settings
from app.schemas.webhook import WebhookListResponse, WebhookSummarySchema
from app.services.webhook_service import list_webhooks_paginated

_settings = get_settings()
_DEFAULT_PAGE_SIZE: int = _settings.default_page_size
_MAX_PAGE_SIZE: int = _settings.max_page_size

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/webhooks", response_model=WebhookListResponse)
async def list_webhooks(
    db: DB,
    page: int = Query(
        1,
        ge=1,
        description="Page number for paginated results.",
        examples=[1],
    ),
    limit: int = Query(
        _DEFAULT_PAGE_SIZE,
        ge=1,
        le=_MAX_PAGE_SIZE,
        description="Maximum number of webhooks returned per page.",
        examples=[_DEFAULT_PAGE_SIZE],
    ),
) -> WebhookListResponse:
    """List webhooks with pagination, ordered by most recently created."""
    webhooks, total = await list_webhooks_paginated(db, page, limit)

    return WebhookListResponse(
        webhooks=[WebhookSummarySchema.model_validate(w) for w in webhooks],
        total=total,
        page=page,
        page_size=limit,
    )


@router.post("/webhooks", status_code=201)
async def create_webhook(db: DB, payload: dict[str, Any]) -> dict[str, str]:
    # Create a new webhook
    # Placeholder for actual implementation
    return {"message": "Webhook created successfully"}


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: str, db: DB) -> None:
    # Delete a webhook by its ID
    # Placeholder for actual implementation
    return None
