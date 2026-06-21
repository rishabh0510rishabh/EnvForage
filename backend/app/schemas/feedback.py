"""Pydantic schemas for uninstall feedback."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    rating: int | None = Field(
        None,
        description="Rating from 1 to 5.",
        ge=1,
        le=5,
        examples=[4],
    )
    reasons: list[str] = Field(
        ...,
        description="List of selected reasons for uninstallation.",
        examples=[["bugs", "slow"]],
    )
    comments: str | None = Field(
        None,
        description="Optional additional comments from the user.",
        examples=["The CLI crashed on windows local installation check."],
    )
    email: str | None = Field(
        None,
        description="Optional contact email of the user.",
        examples=["user@example.com"],
    )


class FeedbackResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Unique ID of the feedback entry.")
    rating: int | None = Field(None, description="Rating from 1 to 5.")
    reasons: list[str] = Field(..., description="List of reasons selected.")
    comments: str | None = Field(None, description="Optional comments.")
    email: str | None = Field(None, description="Optional email.")
    created_at: datetime = Field(..., description="Timestamp when created.")

    class Config:
        from_attributes = True
