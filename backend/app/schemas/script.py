"""Pydantic schemas for script generation API."""
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

OSTarget = Literal["LINUX", "WSL", "WIN"]
OutputFormat = Literal["setup.sh", "setup.ps1", "requirements.txt", "Dockerfile", "devcontainer.json", "pyproject.toml"]


class GenerationRequest(BaseModel):
    """Request body for POST /scripts/generate."""
    profile_id: str = Field(..., description="Profile slug, e.g. 'pytorch-cuda'")
    target_os: OSTarget
    python_version: str = Field(..., pattern=r"^\d+\.\d+$", examples=["3.11"])
    cuda_version: str | None = Field(
        None, pattern=r"^\d+\.\d+$", examples=["12.1"]
    )
    overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Package version overrides, e.g. {'torch': '2.2.0'}",
    )
    output_formats: list[OutputFormat] = Field(
        default=["setup.sh", "requirements.txt"],
        min_length=1,
    )


class ResolvedPackage(BaseModel):
    name: str
    version: str
    cuda_variant: str | None = None


class ScriptPreview(BaseModel):
    filename: str
    content: str
    size_bytes: int


class GenerationResponse(BaseModel):
    """Response for POST /scripts/generate."""
    job_id: uuid.UUID
    status: Literal["completed", "failed"]
    profile_slug: str
    target_os: OSTarget
    python_version: str
    cuda_version: str | None
    resolved_packages: list[ResolvedPackage]
    scripts: list[ScriptPreview]
    warnings: list[str] = Field(default_factory=list)
    download_url: str


class GenerationErrorResponse(BaseModel):
    """Response when compatibility resolution fails."""
    error: dict[str, Any]  # Structured IncompatibilityError details
