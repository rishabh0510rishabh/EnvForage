"""
Profile service — business logic for profile CRUD operations.
"""
import uuid
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.profile import EnvironmentProfile, ProfilePackage
from app.schemas.profile import ProfileFilters


async def list_profiles(
    db: AsyncSession,
    filters: ProfileFilters,
) -> tuple[list[EnvironmentProfile], int]:
    """
    List environment profiles with optional filtering and pagination.
    Returns (profiles, total_count).
    """
    query = (
        select(EnvironmentProfile)
        .where(EnvironmentProfile.deleted_at.is_(None))
        .where(EnvironmentProfile.status == "ACTIVE")
        .options(selectinload(EnvironmentProfile.packages))
        .order_by(EnvironmentProfile.name)
    )

    if filters.os:
        query = query.where(
            EnvironmentProfile.os_support.contains([filters.os])
        )

    if filters.cuda_required is not None:
        query = query.where(
            EnvironmentProfile.cuda_required == filters.cuda_required
        )

    if filters.tags:
        for tag in filters.tags:
            query = query.where(
                EnvironmentProfile.tags.contains([tag])
            )

    # Count total (before pagination)
    count_result = await db.execute(
        select(EnvironmentProfile.id)
        .where(EnvironmentProfile.deleted_at.is_(None))
        .where(EnvironmentProfile.status == "ACTIVE")
    )
    total = len(count_result.all())

    # Apply pagination
    offset = (filters.page - 1) * filters.limit
    query = query.offset(offset).limit(filters.limit)

    result = await db.execute(query)
    profiles = list(result.scalars().all())
    return profiles, total


async def list_all_active_profiles(db: AsyncSession) -> list[EnvironmentProfile]:
    """Fetch all active profiles with their packages, without pagination.

    Used by the /diagnose endpoint to iterate every profile through the
    CompatibilityResolver.
    """
    result = await db.execute(
        select(EnvironmentProfile)
        .where(EnvironmentProfile.deleted_at.is_(None))
        .where(EnvironmentProfile.status == "ACTIVE")
        .options(selectinload(EnvironmentProfile.packages))
        .order_by(EnvironmentProfile.name)
    )
    return list(result.scalars().all())


async def get_profile_by_slug(
    db: AsyncSession,
    slug: str,
) -> EnvironmentProfile | None:
    """Get a single profile by slug, including packages."""
    result = await db.execute(
        select(EnvironmentProfile)
        .where(EnvironmentProfile.slug == slug)
        .where(EnvironmentProfile.deleted_at.is_(None))
        .options(selectinload(EnvironmentProfile.packages))
    )
    return result.scalar_one_or_none()


async def get_profile_by_id(
    db: AsyncSession,
    profile_id: uuid.UUID,
) -> EnvironmentProfile | None:
    """Get a single profile by UUID, including packages."""
    result = await db.execute(
        select(EnvironmentProfile)
        .where(EnvironmentProfile.id == profile_id)
        .where(EnvironmentProfile.deleted_at.is_(None))
        .options(selectinload(EnvironmentProfile.packages))
    )
    return result.scalar_one_or_none()
