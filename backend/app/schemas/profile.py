"""Pydantic schemas for environment profiles API."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

# ── Package schemas ────────────────────────────────────────────────────────────


class PackageSpecSchema(BaseModel):
    package_name: str = Field(
        ...,
        pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$",
        description="Name of the package to install.",
        examples=["torch"],
    )
    version_spec: str = Field(
        ...,
        description="Version constraint or pinned version for the package.",
        examples=["==2.1.0"],
    )
    cuda_variant: str | None = Field(
        None,
        description="Optional CUDA-specific package variant.",
        examples=["cu121"],
    )
    is_optional: bool = Field(
        False,
        description="Whether the package is optional for this profile.",
        examples=[False],
    )
    install_order: int = Field(
        0,
        description="Installation order for this package.",
        examples=[1],
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "package_name": "torch",
                "version_spec": "==2.1.0",
                "cuda_variant": "cu121",
                "is_optional": False,
                "install_order": 1,
            }
        },
    }


# ── Profile schemas ────────────────────────────────────────────────────────────


class ProfileCreateSchema(BaseModel):
    """Schema for creating a new profile."""

    slug: str = Field(
        ...,
        max_length=64,
        description="Unique URL-safe identifier for the environment profile.",
        examples=["pytorch-cu121"],
    )
    name: str = Field(
        ...,
        max_length=128,
        description="Human-readable name of the environment profile.",
        examples=["PyTorch CUDA 12.1"],
    )
    description: str | None = Field(
        None,
        description="Optional summary describing the profile purpose.",
        examples=["GPU-ready PyTorch environment for CUDA 12.1."],
    )
    tags: list[str] | None = Field(
        None,
        description="Tags used to categorize and filter the profile.",
        examples=[["ml", "cuda", "pytorch"]],
    )
    os_support: list[str] = Field(
        ...,
        description="Supported operating systems for this profile.",
        examples=[["LINUX", "WSL"]],
    )
    cuda_required: bool = Field(
        False,
        description="Whether this profile requires CUDA support.",
        examples=[True],
    )
    python_versions: list[str] = Field(
        ...,
        description="Supported Python versions for this profile.",
        examples=[["3.10", "3.11"]],
    )
    cuda_versions: list[str] | None = Field(
        None,
        description="Supported CUDA versions for this profile, if applicable.",
        examples=[["12.1"]],
    )
    packages: list[PackageSpecSchema] = Field(
        default_factory=list,
        description="Ordered list of packages required by this profile.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "slug": "pytorch-cu121",
                "name": "PyTorch CUDA 12.1",
                "description": "GPU-ready PyTorch environment for CUDA 12.1.",
                "tags": ["ml", "cuda", "pytorch"],
                "os_support": ["LINUX", "WSL"],
                "cuda_required": True,
                "python_versions": ["3.10", "3.11"],
                "cuda_versions": ["12.1"],
                "packages": [
                    {
                        "package_name": "torch",
                        "version_spec": "==2.1.0",
                        "cuda_variant": "cu121",
                        "is_optional": False,
                        "install_order": 1,
                    }
                ],
            }
        }
    }


class ProfileUpdateSchema(BaseModel):
    """Schema for partially updating an existing profile (all fields optional)."""

    name: str | None = Field(
        None,
        max_length=128,
        description="Human-readable name of the environment profile.",
        examples=["PyTorch CUDA 12.1"],
    )
    description: str | None = Field(
        None,
        description="Optional summary describing the profile purpose.",
        examples=["GPU-ready PyTorch environment for CUDA 12.1."],
    )
    tags: list[str] | None = Field(
        None,
        description="Tags used to categorize and filter the profile.",
        examples=[["ml", "cuda", "pytorch"]],
    )
    os_support: list[str] | None = Field(
        None,
        description="Supported operating systems for this profile.",
        examples=[["LINUX", "WSL"]],
    )
    cuda_required: bool | None = Field(
        None,
        description="Whether this profile requires CUDA support.",
        examples=[True],
    )
    python_versions: list[str] | None = Field(
        None,
        description="Supported Python versions for this profile.",
        examples=[["3.10", "3.11"]],
    )
    cuda_versions: list[str] | None = Field(
        None,
        description="Supported CUDA versions for this profile, if applicable.",
        examples=[["12.1"]],
    )
    packages: list[PackageSpecSchema] | None = Field(
        None,
        description="Ordered list of packages required by this profile. Replaces all existing packages when provided.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "PyTorch CUDA 12.1 (Updated)",
                "tags": ["ml", "cuda", "pytorch", "updated"],
            }
        }
    }


class ProfileSummarySchema(BaseModel):
    """Lightweight profile for list responses."""

    id: uuid.UUID = Field(
        ...,
        description="Unique database identifier for the profile.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    slug: str = Field(
        ...,
        description="Unique URL-safe identifier for the environment profile.",
        examples=["pytorch-cu121"],
    )
    name: str = Field(
        ...,
        description="Human-readable name of the environment profile.",
        examples=["PyTorch CUDA 12.1"],
    )
    description: str | None = Field(
        None,
        description="Optional summary describing the profile purpose.",
        examples=["GPU-ready PyTorch environment for CUDA 12.1."],
    )
    tags: list[str] | None = Field(
        None,
        description="Tags used to categorize and filter the profile.",
        examples=[["ml", "cuda", "pytorch"]],
    )
    os_support: list[str] = Field(
        ...,
        description="Supported operating systems for this profile.",
        examples=[["LINUX", "WSL"]],
    )
    cuda_required: bool = Field(
        ...,
        description="Whether this profile requires CUDA support.",
        examples=[True],
    )
    python_versions: list[str] = Field(
        ...,
        description="Supported Python versions for this profile.",
        examples=[["3.10", "3.11"]],
    )
    cuda_versions: list[str] | None = Field(
        None,
        description="Supported CUDA versions for this profile, if applicable.",
        examples=[["12.1"]],
    )
    status: str = Field(
        ...,
        description="Validation status of the profile.",
        examples=["active"],
    )
    last_validated: date | None = Field(
        None,
        description="Date when the profile was last validated.",
        examples=["2026-05-26"],
    )

    model_config = {"from_attributes": True}


class ProfileDetailSchema(ProfileSummarySchema):
    """Full profile including package list."""

    packages: list[PackageSpecSchema] = Field(
        ...,
        description="Ordered package list required by this profile.",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the profile was created.",
        examples=["2026-05-26T10:30:00Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the profile was last updated.",
        examples=["2026-05-26T10:30:00Z"],
    )

    model_config = {"from_attributes": True}


# ── List response ──────────────────────────────────────────────────────────────


class ProfileListResponse(BaseModel):
    profiles: list[ProfileSummarySchema] = Field(
        ...,
        description="Profiles returned for the current page.",
    )
    total: int = Field(
        ...,
        description="Total number of profiles matching the filters.",
        examples=[25],
    )
    page: int = Field(
        ...,
        description="Current page number.",
        examples=[1],
    )
    page_size: int = Field(
        ...,
        description="Maximum number of profiles returned per page.",
        examples=[20],
    )


# ── Query filters ──────────────────────────────────────────────────────────────


class ProfileFilters(BaseModel):
    tags: list[str] | None = Field(
        None,
        description="Filter profiles by one or more tags.",
        examples=[["ml", "cuda"]],
    )
    os: str | None = Field(
        None,
        description="Filter by OS: LINUX | WSL | WIN",
        examples=["LINUX"],
    )
    cuda_required: bool | None = Field(
        None,
        description="Filter profiles based on whether CUDA support is required.",
        examples=[True],
    )
    page: int = Field(
        1,
        ge=1,
        description="Page number for paginated results.",
        examples=[1],
    )
    limit: int = Field(
        20,
        ge=1,
        le=100,
        description="Maximum number of profiles returned per page.",
        examples=[20],
    )
