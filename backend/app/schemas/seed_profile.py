"""Pydantic schemas for validating backend/seeds/profiles.yaml."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_OS = frozenset({"LINUX", "WSL", "WIN", "MACOS"})


class ProfilePackageSeedSchema(BaseModel):
    """Package entry as defined in profiles.yaml."""

    name: str = Field(..., min_length=1, max_length=128)
    version_spec: str = Field(..., min_length=1, max_length=64)
    cuda_variant: str | None = Field(None, max_length=32)
    is_optional: bool = False
    install_order: int = Field(0, ge=0)


class ProfileSeedSchema(BaseModel):
    """Single environment profile entry from profiles.yaml."""

    slug: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    os_support: list[str] = Field(..., min_length=1)
    cuda_required: bool = False
    python_versions: list[str] = Field(..., min_length=1)
    cuda_versions: list[str] = Field(default_factory=list)
    status: Literal["ACTIVE", "DEPRECATED"] = "ACTIVE"
    last_validated: date | None = None
    packages: list[ProfilePackageSeedSchema] = Field(default_factory=list)

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError("description must be a string")
        return value.strip()

    @field_validator("os_support")
    @classmethod
    def validate_os_support(cls, value: list[str]) -> list[str]:
        invalid = [os_name for os_name in value if os_name not in ALLOWED_OS]
        if invalid:
            allowed = ", ".join(sorted(ALLOWED_OS))
            raise ValueError(
                f"Invalid os_support values: {invalid}. Allowed: {allowed}"
            )
        return value


class ProfilesYamlSchema(BaseModel):
    """Root structure of profiles.yaml."""

    profiles: list[ProfileSeedSchema]

class GenerationRequest(BaseModel):
    """Schema for validating a generation request payload."""
    target_os: Literal["Linux", "Windows", "WSL", "macOS"]
    framework: str = Field(..., min_length=1, max_length=64)
    cuda_version: str = Field(..., min_length=1, max_length=16)
