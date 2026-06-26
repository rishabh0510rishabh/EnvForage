"""Pydantic schemas for the webhooks API."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WebhookSummarySchema(BaseModel):
    """A single webhook returned in list responses."""

    id: uuid.UUID
    target_url: str
    events: list[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookListResponse(BaseModel):
    """Paginated response for GET /webhooks."""

    webhooks: list[WebhookSummarySchema] = Field(
        ...,
        description="Webhooks returned for the current page.",
    )
    total: int = Field(
        ...,
        description="Total number of webhooks matching the query.",
        examples=[5],
    )
    page: int = Field(
        ...,
        description="Current page number.",
        examples=[1],
    )
    page_size: int = Field(
        ...,
        description="Maximum number of webhooks returned per page.",
        examples=[20],
    )
