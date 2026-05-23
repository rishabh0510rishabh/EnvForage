"""
Profile service — business logic for profile CRUD operations.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.profile import EnvironmentProfile, ProfilePackage
from app.schemas.profile import ProfileCreateSchema, ProfileFilters


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
    return True
