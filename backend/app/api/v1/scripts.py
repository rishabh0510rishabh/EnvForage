"""Script generation endpoint — POST /api/v1/scripts/generate."""

import io
import zipfile
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import StreamingResponse

from app.api.deps import DB
from app.compatibility.errors import (
    IncompatibilityError,
    UnknownVersionError,
    UnsupportedOSError,
)
from app.middleware.rate_limit import general_rate_limit
from app.schemas.script import GenerationRequest, GenerationResponse
from app.services import profile_service, script_service

router = APIRouter()


def _stream_zip(buffer: io.BytesIO) -> Iterator[bytes]:
    """Stream ZIP contents and ensure buffer cleanup."""
    try:
        yield buffer.getvalue()
    finally:
        buffer.close()


@router.post(
    "/scripts/generate",
    response_model=GenerationResponse,
    status_code=201,
    summary="Generate environment setup scripts",
    description=(
        "Generate platform-specific setup scripts for an environment profile "
        "after validating compatibility constraints."
    ),
    tags=["Scripts"],
    responses={
        201: {"description": "Scripts generated successfully"},
        404: {"description": "Profile not found"},
        409: {"description": "Compatibility validation failed"},
        422: {"description": "Request validation error"},
    },
)

async def generate_scripts(
    request: GenerationRequest,
    db: DB,
    _rate_limit: None = Depends(general_rate_limit),
) -> GenerationResponse:
    """
    Generate a set of setup scripts for a given profile and target configuration.

    The Compatibility Engine validates all version constraints before rendering.
    Any incompatibility is returned as a structured 409 error.
    """
    # Load profile
    profile = await profile_service.get_profile_by_slug(db, request.profile_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "PROFILE_NOT_FOUND",
                    "message": f"Profile '{request.profile_id}' not found",
                }
            },
        )

    # Generate (may raise compatibility errors)
    try:
        result = await script_service.generate_scripts(db, profile, request)
    except UnsupportedOSError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "UNSUPPORTED_OS",
                    "message": str(e),
                    "details": {
                        "profile": e.profile_slug,
                        "requested_os": e.requested_os,
                        "supported_os": e.supported_os,
                    },
                }
            },
        ) from e
    except (IncompatibilityError, UnknownVersionError) as e:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "INCOMPATIBLE_VERSIONS",
                    "message": str(e),
                    "details": (
                        e.to_dict()
                        if isinstance(e, IncompatibilityError)
                        else {"component": e.component, "version": e.version}
                    ),
                }
            },
        ) from e

    return result


@router.get(
    "/scripts/{job_id}/download",
    summary="Download generated script bundle",
    description=(
        "Download a ZIP archive containing generated setup scripts "
        "and manifest information."
    ),
    tags=["Scripts"],
    responses={
        200: {"description": "Script ZIP archive downloaded successfully"},
        400: {"description": "Invalid script generation job ID"},
        404: {"description": "Script generation job not found"},
    },
)
async def download_scripts(
    db: DB,
    job_id: str = Path(
        ...,
        description="Script generation job UUID.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    ),
) -> StreamingResponse:
    """
    Download a generated script bundle as a ZIP file.
    """
    import uuid

    from sqlalchemy import select

    from app.models.script_job import ScriptGenerationJob

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(ScriptGenerationJob)
        .where(ScriptGenerationJob.id == job_uuid)
        .options(selectinload(ScriptGenerationJob.scripts))
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Build ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for script in job.scripts:
            zf.writestr(script.filename, script.content)
        # Include a manifest
        manifest = (
            f"EnvForge Generated Scripts\n"
            f"Job: {job.id}\n"
            f"Profile: {job.profile_id}\n"
            f"OS: {job.target_os}\n"
            f"Python: {job.python_version}\n"
        )
        zf.writestr("MANIFEST.txt", manifest)

    zip_buffer.seek(0)
    return StreamingResponse(
        _stream_zip(zip_buffer),
        media_type="application/zip",
        headers={
            "Content-Disposition": (f"attachment; filename=envforge_{job_id[:8]}.zip")
        },
    )
