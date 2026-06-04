"""
Profile service — business logic for profile CRUD operations.
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cache import get_redis_client
from app.models.profile import EnvironmentProfile, ProfilePackage
from app.schemas.profile import (
    ProfileCreateSchema,
    ProfileDetailSchema,
    ProfileFilters,
    ProfileSummarySchema,
)


async def get_all_active_profiles(
    db: AsyncSession,
    include_packages: bool = False,
) -> list[EnvironmentProfile]:
    """Get all active profiles directly without pagination or count overhead."""
    query = (
        select(EnvironmentProfile)
        .where(EnvironmentProfile.deleted_at.is_(None))
        .where(EnvironmentProfile.status == "ACTIVE")
        .order_by(EnvironmentProfile.name)
    )
    if include_packages:
        query = query.options(selectinload(EnvironmentProfile.packages))

    result = await db.execute(query)
    return list(result.scalars().all())


async def list_cached_profiles(
    db: AsyncSession,
    filters: ProfileFilters,
    include_packages: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    """
    List environment profiles with optional filtering and pagination.
    Returns cached response if available. Returns (profiles_dicts, total_count).
    """
    redis = await get_redis_client()
    cache_key = None
    if redis:
        filter_dict = filters.model_dump()
        filter_str = json.dumps(filter_dict, sort_keys=True)
        cache_key = f"profiles:list:inc_pkgs={include_packages}:{filter_str}"
        cached_data = await redis.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            return data["profiles"], data["total"]

    profiles, total = await list_profiles(db, filters, include_packages)

    if include_packages:
        profiles_data = [ProfileDetailSchema.model_validate(p).model_dump(mode="json") for p in profiles]
    else:
        profiles_data = [ProfileSummarySchema.model_validate(p).model_dump(mode="json") for p in profiles]

    if redis and cache_key:
        cache_data = {"profiles": profiles_data, "total": total}
        await redis.setex(cache_key, 300, json.dumps(cache_data))

    return profiles_data, total


async def list_profiles(
    db: AsyncSession,
    filters: ProfileFilters,
    include_packages: bool = False,
) -> tuple[list[Any], int]:
    """
    List environment profiles with optional filtering and pagination.
    Returns strictly ORM objects (profiles, total_count).
    """
    redis = await get_redis_client()
    cache_key = None
    if redis:
        filter_dict = filters.model_dump()
        filter_str = json.dumps(filter_dict, sort_keys=True)
        cache_key = f"profiles:list:{filter_str}"
        cached_data = await redis.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            return data["profiles"], data["total"]

    query = (
        select(EnvironmentProfile)
        .where(EnvironmentProfile.deleted_at.is_(None))
        .where(EnvironmentProfile.status == "ACTIVE")
        .order_by(EnvironmentProfile.name)
    )

    if include_packages:
        query = query.options(selectinload(EnvironmentProfile.packages))

    if filters.os:
        query = query.where(EnvironmentProfile.os_support.contains([filters.os]))

    if filters.cuda_required is not None:
        query = query.where(EnvironmentProfile.cuda_required == filters.cuda_required)

    if filters.tags:
        for tag in filters.tags:
            query = query.where(EnvironmentProfile.tags.contains([tag]))

    # Count total (before pagination) - apply same filters as main query
    from sqlalchemy import func

    count_query = (
        select(func.count(EnvironmentProfile.id))
        .where(EnvironmentProfile.deleted_at.is_(None))
        .where(EnvironmentProfile.status == "ACTIVE")
    )
    if filters.os:
        count_query = count_query.where(
            EnvironmentProfile.os_support.contains([filters.os])
        )
    if filters.cuda_required is not None:
        count_query = count_query.where(
            EnvironmentProfile.cuda_required == filters.cuda_required
        )
    if filters.tags:
        for tag in filters.tags:
            count_query = count_query.where(EnvironmentProfile.tags.contains([tag]))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Apply pagination
    offset = (filters.page - 1) * filters.limit
    query = query.offset(offset).limit(filters.limit)

    result = await db.execute(query)
    profiles = list(result.scalars().all())

    if redis and cache_key:
        profiles_data = [ProfileSummarySchema.model_validate(p).model_dump(mode="json") for p in profiles]
        cache_data = {"profiles": profiles_data, "total": total}
        await redis.setex(cache_key, 300, json.dumps(cache_data))

    return profiles, total

async def get_cached_profile_by_slug(
    db: AsyncSession,
    slug: str,
) -> dict[str, Any] | None:
    """Get a single profile by slug (from cache if available) returning dictionary."""
    redis = await get_redis_client()
    cache_key = f"profiles:slug:{slug}"
    if redis:
        cached_data = await redis.get(cache_key)
        if cached_data:
            return cast(dict[str, Any], json.loads(cached_data))

    profile = await get_profile_by_slug(db, slug)

    if not profile:
        return None

    profile_data = ProfileDetailSchema.model_validate(profile).model_dump(mode="json")
    if redis:
        await redis.setex(cache_key, 300, json.dumps(profile_data))

    return profile_data


async def get_profile_by_slug(
    db: AsyncSession,
    slug: str,
) -> Any | None:
    """Get a single profile by slug, including packages."""
    redis = await get_redis_client()
    cache_key = f"profiles:slug:{slug}"
    if redis:
        cached_data = await redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

    result = await db.execute(
        select(EnvironmentProfile)
        .where(EnvironmentProfile.slug == slug)
        .where(EnvironmentProfile.deleted_at.is_(None))
        .options(selectinload(EnvironmentProfile.packages))
    )
    profile = result.scalar_one_or_none()

    if redis and profile:
        profile_data = ProfileDetailSchema.model_validate(profile).model_dump(mode="json")
        await redis.setex(cache_key, 300, json.dumps(profile_data))

    return profile

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


async def _invalidate_profile_caches(slug: str | None = None) -> None:
    redis = await get_redis_client()
    if not redis:
        return
    if slug:
        await redis.delete(f"profiles:slug:{slug}")
    async for key in redis.scan_iter("profiles:list:*"):
        await redis.delete(key)


async def create_profile(
    db: AsyncSession,
    profile_in: ProfileCreateSchema,
) -> EnvironmentProfile:
    """Create a new profile."""
    # Create main profile entity
    profile_data = profile_in.model_dump(exclude={"packages"})
    db_profile = EnvironmentProfile(**profile_data)

    # Create associated packages
    for pkg_in in profile_in.packages:
        pkg_data = pkg_in.model_dump()
        db_pkg = ProfilePackage(**pkg_data)
        db_profile.packages.append(db_pkg)

    db.add(db_profile)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    # Fetch the profile again with packages selectinloaded to avoid lazy-loading errors
    profile = await get_profile_by_id(db, db_profile.id)
    if not profile:
        raise ValueError("Failed to retrieve created profile")

    await _invalidate_profile_caches(profile.slug)
    return profile


async def delete_profile(
    db: AsyncSession,
    slug: str,
) -> bool:
    """Soft delete a profile by slug. Returns True if deleted, False if not found."""
    profile = await get_profile_by_slug(db, slug)
    if not profile:
        return False

    profile.deleted_at = datetime.now(UTC)
    profile.status = "DELETED"

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await _invalidate_profile_caches(slug)
    return True
