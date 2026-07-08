"""Service layer for webhook listing with pagination."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook


async def list_webhooks_paginated(
    db: AsyncSession, page: int, limit: int
) -> tuple[list[Webhook], int]:
    """
    Return a page of webhooks ordered by most recently created, plus the
    total count of all webhooks (for building pagination metadata).
    """
    offset = (page - 1) * limit

    total_result = await db.execute(select(func.count()).select_from(Webhook))
    total = total_result.scalar_one()

    result = await db.execute(
        select(Webhook)
        .order_by(Webhook.created_at.desc(), Webhook.id.desc())
        .offset(offset)
        .limit(limit)
    )
    webhooks = list(result.scalars().all())

    return webhooks, total
