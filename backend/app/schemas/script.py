"""Pydantic schemas for script generation API."""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

OSTarget = Literal["LINUX", "WSL", "WIN"]

OutputFormat = Literal[
    "setup.sh",
    "setup.ps1",
    "requirements.txt",
    "Dockerfile",
    "Makefile",
    "environment.yml",
    "docker-compose.yml",
    "devcontainer.json",
    ".gitignore",
    "pyproject.poetry.toml",
]


class GenerationRequest(BaseModel):
    """Request body for POST /scripts/generate."""

    profile_id: str = Field(
        ...,
        description="Environment profile slug.",
        examples=["pytorch-cu121"],
    )

    target_os: OSTarget = Field(
        ...,
        description="Target operating system for script generation.",
        examples=["LINUX"],
    )

    python_version: str = Field(
        ...,
        pattern=r"^\d+\.\d+$",
        description="Target Python version.",
        examples=["3.11"],
    )

    cuda_version: str | None = Field(
        None,
        pattern=r"^\d+\.\d+$",
        description="Target CUDA version if CUDA support is required.",
        examples=["12.1"],
    )

    overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Optional package version overrides.",
        examples=[{"torch": "2.2.0"}],
    )

    output_formats: list[OutputFormat] = Field(
        default=["setup.sh", "requirements.txt"],
        min_length=1,
        description="List of files to generate.",
        examples=[["setup.sh", "requirements.txt"]],
    )

    use_uv: bool = Field(
        default=False,
        description="Use uv instead of pip for dependency installation.",
        examples=[False],
    )
    use_micromamba: bool = Field(
        default=False,
        description="Use micromamba instead of standard Conda/Miniconda for environment management",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "profile_id": "pytorch-cu121",
                "target_os": "LINUX",
                "python_version": "3.11",
                "cuda_version": "12.1",
                "overrides": {
                    "torch": "2.2.0",
                },
                "output_formats": [
                    "setup.sh",
                    "requirements.txt",
                ],
                "use_uv": False,
            }
        }
    }


class ResolvedPackage(BaseModel):
    name: str = Field(
        ...,
        description="Resolved package name.",
        examples=["torch"],
    )

    version: str = Field(
        ...,
        description="Resolved package version.",
        examples=["2.2.0"],
    )

    cuda_variant: str | None = Field(
        None,
        description="CUDA-specific package build variant.",
        examples=["cu121"],
    )


class ScriptPreview(BaseModel):
    filename: str = Field(
        ...,
        description="Generated script filename.",
        examples=["setup.sh"],
    )

    content: str = Field(
        ...,
        description="Generated script content preview.",
        examples=["#!/usr/bin/env bash"],
    )

    size_bytes: int = Field(
        ...,
        description="Size of the generated file in bytes.",
        examples=[512],
    )

    security_score: Literal["Low", "Medium", "High"] = Field(
        ...,
        description="Assessed risk level based on script content analysis.",
        examples=["Low"],
    )


class GenerationResponse(BaseModel):
    """Response for POST /scripts/generate."""

    job_id: uuid.UUID = Field(
        ...,
        description="Unique script generation job identifier.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    status: Literal["completed", "failed"] = Field(
        ...,
        description="Generation job status.",
        examples=["completed"],
    )

    profile_slug: str = Field(
        ...,
        description="Profile slug used for generation.",
        examples=["pytorch-cu121"],
    )

    target_os: OSTarget = Field(
        ...,
        description="Target operating system used for generation.",
        examples=["LINUX"],
    )

    python_version: str = Field(
        ...,
        description="Resolved Python version.",
        examples=["3.11"],
    )

    cuda_version: str | None = Field(
        None,
        description="Resolved CUDA version.",
        examples=["12.1"],
    )

    resolved_packages: list[ResolvedPackage] = Field(
        ...,
        description="Packages resolved during compatibility validation.",
    )

    scripts: list[ScriptPreview] = Field(
        ...,
        description="Generated script previews.",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings generated during script creation.",
        examples=[["CUDA driver version is close to minimum supported version"]],
    )

    download_url: str = Field(
        ...,
        description="URL used to download the generated script bundle.",
        examples=["/api/v1/scripts/550e8400/download"],
    )


class GenerationErrorResponse(BaseModel):
    """Response when compatibility resolution fails."""

    error: dict[str, Any] = Field(
        ...,
        description="Structured compatibility or validation error payload.",
        examples=[
            {
                "code": "INCOMPATIBLE_VERSIONS",
                "message": "CUDA version is incompatible with selected profile.",
            }
        ],
    )
