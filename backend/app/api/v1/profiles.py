"""Profile endpoints — GET /api/v1/profiles and /api/v1/profiles/{slug}."""

import logging

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.deps import DB, require_admin
from app.core.exceptions import ConflictError, EntityNotFoundError, InternalServerError
from app.middleware.rate_limit import general_rate_limit
from app.schemas.profile import (
    ProfileCreateSchema,
    ProfileDetailSchema,
    ProfileFilters,
    ProfileListResponse,
    ProfileSummarySchema,
    ProfileUpdateSchema,
)
from app.services import profile_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/profiles",
    response_model=ProfileListResponse,
    summary="List environment profiles",
    description=(
        "Retrieve a paginated list of environment profiles with optional "
        "filters for tags, operating system, and CUDA requirement."
    ),
    tags=["Profiles"],
    responses={
        200: {"description": "Profiles retrieved successfully"},
        400: {"description": "Invalid query parameters"},
        422: {"description": "Request validation error"},
    },
)
async def list_profiles(
    db: DB,
    tags: list[str] | None = Query(
        None,
        description="Filter profiles by one or more tags.",
        examples=[["ml", "cuda"]],
    ),
    os: str | None = Query(
        None,
        description=(
            "Filter profiles by operating system. Supported values: LINUX, WSL, WIN."
        ),
        examples=["LINUX"],
    ),
    cuda_required: bool | None = Query(
        None,
        description="Filter profiles based on whether CUDA support is required.",
        examples=[True],
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number for paginated results.",
        examples=[1],
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of profiles returned per page.",
        examples=[20],
    ),
) -> ProfileListResponse:
    """
    List all available environment profiles.

    Supports filtering by OS, CUDA requirement, and tags.
    """
    filters = ProfileFilters(
        tags=tags, os=os, cuda_required=cuda_required, page=page, limit=limit
    )
    profiles, total = await profile_service.list_cached_profiles(db, filters)

    return ProfileListResponse(
        profiles=[ProfileSummarySchema.model_validate(p) for p in profiles],
        total=total,
        page=page,
        page_size=limit,
    )


@router.get(
    "/profiles/{slug}",
    response_model=ProfileDetailSchema,
    summary="Get profile details",
    description=(
        "Retrieve full details for a single environment profile, including "
        "supported platforms, requirements, and package list."
    ),
    tags=["Profiles"],
    responses={
        200: {"description": "Profile retrieved successfully"},
        404: {"description": "Profile not found"},
    },
)
async def get_profile(
    db: DB,
    slug: str = Path(
        ...,
        description="Unique slug of the environment profile.",
        examples=["pytorch-cu121"],
    ),
) -> ProfileDetailSchema:
    """
    Get full details for a single environment profile including package list.
    """
    profile = await profile_service.get_cached_profile_by_slug(db, slug)
    if profile is None:
        raise EntityNotFoundError(
            resource=f"Profile '{slug}'",
            error_code="PROFILE_NOT_FOUND",
        )
    return ProfileDetailSchema.model_validate(profile)


@router.post(
    "/profiles",
    response_model=ProfileDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create environment profile",
    description=(
        "Create a new environment profile containing platform support, "
        "runtime requirements, and package metadata."
    ),
    tags=["Profiles"],
    responses={
        201: {"description": "Profile created successfully"},
        401: {"description": "Missing or invalid admin API key"},
        409: {"description": "Profile already exists"},
        422: {"description": "Request validation error"},
        500: {"description": "Database error while creating profile"},
        503: {"description": "Admin API key not configured on this server"},
    },
)
async def create_profile(
    profile_in: ProfileCreateSchema,
    db: DB,
    _rate_limit: None = Depends(general_rate_limit),
    _auth: None = Depends(require_admin),
) -> ProfileDetailSchema:
    """
    Create a new environment profile.
    """
    logger.info("Admin write: creating profile slug=%s", profile_in.slug)
    try:
        profile = await profile_service.create_profile(db, profile_in)
        logger.info("Profile created: slug=%s", profile.slug)
        return ProfileDetailSchema.model_validate(profile)
    except IntegrityError as exc:
        await db.rollback()
        logger.warning("Duplicate profile slug: %s", profile_in.slug)
        raise ConflictError(f"Profile '{profile_in.slug}' already exists.") from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Database error while creating profile")
        raise InternalServerError("Failed to create profile.") from exc


@router.delete(
    "/profiles/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete environment profile",
    description="Soft delete an environment profile using its slug.",
    tags=["Profiles"],
    responses={
        204: {"description": "Profile deleted successfully"},
        401: {"description": "Missing or invalid admin API key"},
        404: {"description": "Profile not found"},
        503: {"description": "Admin API key not configured on this server"},
    },
)
async def delete_profile(
    db: DB,
    slug: str = Path(
        ...,
        description="Unique slug of the environment profile to delete.",
        examples=["pytorch-cu121"],
    ),
    _auth: None = Depends(require_admin),
) -> None:
    """
    Soft delete a profile by slug.
    """
    logger.info("Admin write: deleting profile slug=%s", slug)
    deleted = await profile_service.delete_profile(db, slug)
    if not deleted:
        raise EntityNotFoundError(
            resource=f"Profile '{slug}'",
            error_code="PROFILE_NOT_FOUND",
        )
    logger.info("Profile deleted: slug=%s", slug)


@router.patch(
    "/profiles/{slug}",
    response_model=ProfileDetailSchema,
    status_code=status.HTTP_200_OK,
    summary="Update environment profile",
    description="Partially update an environment profile using its slug. Only the fields provided in the request body are changed.",
    tags=["Profiles"],
    responses={
        200: {"description": "Profile updated successfully."},
        401: {"description": "Missing or invalid admin API key."},
        404: {"description": "Profile not found."},
        422: {"description": "Request validation error."},
        503: {"description": "Admin API key not configured on this server."},
    },
)
async def update_profile(
    profile_in: ProfileUpdateSchema,
    db: DB,
    slug: str = Path(
        ...,
        description="Unique slug of the environment profile to update.",
        examples=["pytorch-cu121"],
    ),
    _rate_limit: None = Depends(general_rate_limit),
    _auth: None = Depends(require_admin),
) -> ProfileDetailSchema:
    """
    Partially update an environment profile by slug.

    Only the fields included in the request body are modified;
    omitted fields retain their current values.
    """
    logger.info("Admin write: updating profile slug=%s", slug)
    updated = await profile_service.update_profile(db, slug, profile_in)
    if updated is None:
        raise EntityNotFoundError(
            resource=f"Profile '{slug}'",
            error_code="PROFILE_NOT_FOUND",
        )
    logger.info("Profile updated: slug=%s", slug)
    return ProfileDetailSchema.model_validate(updated)
