"""Profile endpoints — GET /api/v1/profiles and /api/v1/profiles/{slug}."""
import logging

from fastapi import APIRouter, Query, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.deps import DB
from app.core.exceptions import ConflictError, EntityNotFoundError, InternalServerError
from app.schemas.profile import (
    ProfileCreateSchema,
    ProfileDetailSchema,
    ProfileFilters,
    ProfileListResponse,
    ProfileSummarySchema,
)
from app.services import profile_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/profiles", response_model=ProfileListResponse)
async def list_profiles(
    db: DB,
    tags: list[str] | None = Query(None, description="Filter by tags"),
    os: str | None = Query(None, description="Filter by OS: LINUX | WSL | WIN"),
    cuda_required: bool | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> ProfileListResponse:
    """
    List all available environment profiles.

    Supports filtering by OS, CUDA requirement, and tags.
    """
    filters = ProfileFilters(
        tags=tags, os=os, cuda_required=cuda_required, page=page, limit=limit
    )
    profiles, total = await profile_service.list_profiles(db, filters)

    return ProfileListResponse(
        profiles=[ProfileSummarySchema.model_validate(p) for p in profiles],
        total=total,
        page=page,
        page_size=limit,
    )


@router.get("/profiles/{slug}", response_model=ProfileDetailSchema)
async def get_profile(slug: str, db: DB) -> ProfileDetailSchema:
    """
    Get full details for a single environment profile including package list.
    """
    profile = await profile_service.get_profile_by_slug(db, slug)
    if profile is None:
        raise EntityNotFoundError(resource=f"Profile '{slug}'", error_code="PROFILE_NOT_FOUND")
    return ProfileDetailSchema.model_validate(profile)


@router.post(
    "/profiles",
    response_model=ProfileDetailSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(profile_in: ProfileCreateSchema, db: DB) -> ProfileDetailSchema:
    """
    Create a new environment profile.
    """
    try:
        profile = await profile_service.create_profile(db, profile_in)
        return ProfileDetailSchema.model_validate(profile)
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("Duplicate profile slug: %s", profile_in.slug)
        raise ConflictError(f"Profile '{profile_in.slug}' already exists.") from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Database error while creating profile")
        raise InternalServerError("Failed to create profile.") from exc


@router.delete("/profiles/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(slug: str, db: DB) -> None:
    """
    Soft delete a profile by slug.
    """
    deleted = await profile_service.delete_profile(db, slug)
    if not deleted:
        raise EntityNotFoundError(resource=f"Profile '{slug}'", error_code="PROFILE_NOT_FOUND")
