"""Script generation endpoint — POST /api/v1/scripts/generate."""

import io
import uuid
import zipfile
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, get_current_user
from app.middleware.rate_limit import general_rate_limit
from app.models.profile import EnvironmentProfile
from app.schemas.script import GenerationRequest, GenerationResponse
from app.services import script_service

router = APIRouter(dependencies=[Depends(get_current_user)])


def _stream_zip(buffer: io.BytesIO) -> Iterator[bytes]:
    """Stream ZIP contents and ensure buffer cleanup."""
    try:
        yield buffer.getvalue()
    finally:
        buffer.close()


@router.post(
    "/scripts/generate",
    response_model=GenerationResponse,
    status_code=202,
    summary="Generate environment setup scripts (Async)",
    description=(
        "Submits a job to generate platform-specific setup scripts for an "
        "environment profile. Returns a job ID for polling."
    ),
    tags=["Scripts"],
    responses={
        202: {"description": "Script generation job submitted successfully"},
        404: {"description": "Profile not found"},
        422: {"description": "Request validation error"},
    },
)
async def generate_scripts(
    request: GenerationRequest,
    db: DB,
    _rate_limit: None = Depends(general_rate_limit),
) -> GenerationResponse:
    """
    Submit a job to generate setup scripts.
    The task is executed in the background by Celery.
    """
    db_result = await db.execute(
        select(EnvironmentProfile)
        .where(EnvironmentProfile.slug == request.profile_id)
        .where(EnvironmentProfile.deleted_at.is_(None))
    )
    profile = db_result.scalar_one_or_none()
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

    return await script_service.submit_generation_job(db, profile, request)


@router.get(
    "/scripts/{job_id}/status",
    response_model=GenerationResponse,
    summary="Poll script generation job status",
    description="Check the status of a previously submitted script generation job.",
    tags=["Scripts"],
    responses={
        200: {"description": "Job status retrieved successfully"},
        404: {"description": "Job not found"},
    },
)
async def get_generation_status(
    db: DB,
    job_id: uuid.UUID = Path(..., description="Job UUID to check."),
) -> GenerationResponse:
    from app.models.script_job import GeneratedScript, ScriptGenerationJob

    db_result = await db.execute(
        select(ScriptGenerationJob).where(ScriptGenerationJob.id == job_id)
    )
    job = db_result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found"}},
        )

    # Fetch profile slug
    profile_result = await db.execute(
        select(EnvironmentProfile).where(EnvironmentProfile.id == job.profile_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "PROFILE_NOT_FOUND", "message": "Profile not found for this job"}},
        )

    from typing import Any
    resp: dict[str, Any] = {
        "job_id": job.id,
        "status": job.status,
        "profile_slug": profile.slug,
        "target_os": job.target_os,
    }

    if job.status == "completed" and job.resolved_env:
        from app.schemas.script import ResolvedPackage as ResponseResolvedPackage
        from app.schemas.script import ScriptPreview

        resp["python_version"] = job.python_version
        resp["cuda_version"] = job.cuda_version
        resp["resolved_packages"] = [
            ResponseResolvedPackage(
                name=pkg["name"],
                version=pkg["version"],
                cuda_variant=pkg.get("cuda_variant"),
            )
            for pkg in job.resolved_env.get("packages", [])
        ]
        resp["warnings"] = job.resolved_env.get("warnings", [])
        resp["download_url"] = f"/api/v1/scripts/{job.id}/download"

        # Fetch scripts metadata
        scripts_result = await db.execute(
            select(GeneratedScript.filename, GeneratedScript.size_bytes)
            .where(GeneratedScript.job_id == job.id)
        )
        scripts = scripts_result.all()
        resp["scripts"] = [
            ScriptPreview(
                filename=s.filename,
                content="",  # Content preview is omitted in status for efficiency
                size_bytes=s.size_bytes or 0,
            )
            for s in scripts
        ]
    elif job.status == "failed" and job.error:
        resp["error_message"] = job.error

    return GenerationResponse(**resp)


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
    job_id: uuid.UUID = Path(
        ...,
        description="Script generation job UUID.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    ),
) -> StreamingResponse:
    """
    Download a generated script bundle as a ZIP file.
    """

    from sqlalchemy import select

    from app.models.script_job import ScriptGenerationJob

    # FastAPI path parameter handles UUID parsing and validation


    result = await db.execute(
        select(ScriptGenerationJob)
        .where(ScriptGenerationJob.id == job_id)
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
            f"EnvForage Generated Scripts\n"
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
            "Content-Disposition": (f"attachment; filename=envforage_{str(job_id)[:8]}.zip")
        },
    )
