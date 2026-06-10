"""
Sync and Seed Service — seeds compatibility matrices and fetches updates from PyPI/NVIDIA.
"""

import asyncio
import logging
import re
import uuid
from typing import Any

import httpx
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compatibility.matrix.cuda import CUDA_MATRIX
from app.compatibility.matrix.python import PYTHON_MATRIX
from app.compatibility.matrix.rocm import ROCM_MATRIX
from app.compatibility.resolver import clear_compatibility_cache
from app.models.matrix import CUDAMatrixEntry, PythonMatrixEntry, RocmMatrixEntry

logger = logging.getLogger(__name__)


async def seed_compatibility_matrices(db: AsyncSession) -> None:
    """Seed the database compatibility tables from local static files if empty."""
    # 1. Seed CUDA Matrix
    result = await db.execute(select(CUDAMatrixEntry).limit(1))
    if not result.scalars().first():
        logger.info("[seed] Seeding CUDA compatibility matrix...")
        for version, cuda_entry in CUDA_MATRIX.items():
            db.add(
                CUDAMatrixEntry(
                    id=uuid.uuid4(),
                    cuda_version=version,
                    min_driver_linux=cuda_entry.min_driver_linux,
                    min_driver_windows=cuda_entry.min_driver_windows,
                    cudnn_versions=cuda_entry.cudnn_versions,
                    supported_archs=cuda_entry.supported_archs,
                    notes=cuda_entry.notes,
                    source_url=cuda_entry.source_url,
                )
            )

    # 2. Seed ROCm Matrix
    result = await db.execute(select(RocmMatrixEntry).limit(1))
    if not result.scalars().first():
        logger.info("[seed] Seeding ROCm compatibility matrix...")
        for version, rocm_entry in ROCM_MATRIX.items():
            db.add(
                RocmMatrixEntry(
                    id=uuid.uuid4(),
                    rocm_version=version,
                    min_driver_linux=rocm_entry.min_driver_linux,
                    supported_gpus=rocm_entry.supported_gpus,
                    notes=rocm_entry.notes,
                    source_url=rocm_entry.source_url or "",
                )
            )

    # 3. Seed Python/Framework Matrix
    result = await db.execute(select(PythonMatrixEntry).limit(1))
    if not result.scalars().first():
        logger.info("[seed] Seeding Python compatibility matrix...")
        for framework, entries in PYTHON_MATRIX.items():
            for py_entry in entries:
                db.add(
                    PythonMatrixEntry(
                        id=uuid.uuid4(),
                        framework=framework,
                        version=py_entry.version,
                        min_python=py_entry.min_python,
                        max_python=py_entry.max_python,
                        supported_cuda=py_entry.supported_cuda,
                        supported_rocm=py_entry.supported_rocm,
                        supported_python=py_entry.supported_python,
                    )
                )

    await db.commit()


def parse_supported_python(requires_python: str | None) -> list[str]:
    """Parse requires_python constraint string and return matching Python versions."""
    all_py_versions = ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]
    if not requires_python:
        return all_py_versions
    try:
        spec = SpecifierSet(requires_python)
        supported = [v for v in all_py_versions if Version(v) in spec]
        return supported
    except Exception as e:
        logger.error(f"Sync service error: {e}")
        return []


async def sync_pypi_releases(db: AsyncSession) -> None:
    """Fetch recent releases from PyPI and append new entries."""
    frameworks = ["torch", "tensorflow", "jax", "diffusers"]
    async with httpx.AsyncClient(timeout=10.0) as client:
        for framework in frameworks:
            try:
                url = f"https://pypi.org/pypi/{framework}/json"
                response = await client.get(url)
                if response.status_code != 200:
                    logger.warning(
                        "Failed to fetch PyPI data for %s: %s",
                        framework,
                        response.status_code,
                    )
                    continue

                data = response.json()
                releases = data.get("releases", {})
                if not releases:
                    continue

                # Get all existing versions in database for this framework
                db_result = await db.execute(
                    select(PythonMatrixEntry).where(
                        PythonMatrixEntry.framework == framework
                    )
                )
                existing_versions = {e.version for e in db_result.scalars().all()}

                # Sort releases by Version helper to find the latest
                sorted_releases = []
                for v_str in releases.keys():
                    try:
                        sorted_releases.append((Version(v_str), v_str))
                    except Exception as e:
                        logger.error(f"Sync error 1: {e}")
                        pass
                sorted_releases.sort()

                new_entries = 0
                for ver, v_str in sorted_releases:
                    if v_str in existing_versions:
                        continue

                    # Filter out pre-releases, dev releases, and post-releases to keep matrix clean
                    if ver.is_prerelease or ver.is_devrelease or ver.is_postrelease:
                        continue

                    # Get requires_python from the release details if possible
                    release_info = releases[v_str]
                    requires_python = None
                    if isinstance(release_info, list) and len(release_info) > 0:
                        requires_python = release_info[0].get("requires_python")

                    # If not in release list, query the specific release endpoint to be extra thorough
                    if not requires_python:
                        try:
                            rel_url = f"https://pypi.org/pypi/{framework}/{v_str}/json"
                            rel_resp = await client.get(rel_url)
                            if rel_resp.status_code == 200:
                                requires_python = (
                                    rel_resp.json()
                                    .get("info", {})
                                    .get("requires_python")
                                )
                        except Exception as e:
                            logger.error(f"Sync error 2: {e}")
                            pass

                    supported_py = parse_supported_python(requires_python)
                    if not supported_py:
                        continue
                    min_py = supported_py[0]
                    max_py = supported_py[-1]

                    # Heuristic for CUDA and ROCm support:
                    # Inherit from the closest previous version of the framework in the DB
                    closest_cuda = []
                    closest_rocm = []
                    db_prev = await db.execute(
                        select(PythonMatrixEntry)
                        .where(PythonMatrixEntry.framework == framework)
                        .order_by(PythonMatrixEntry.created_at.desc())
                    )
                    prev_entries = db_prev.scalars().all()
                    if prev_entries:
                        # Find closest version by major/minor
                        best_match = prev_entries[0]
                        for entry in prev_entries:
                            try:
                                if (
                                    Version(entry.version).major == ver.major
                                    and Version(entry.version).minor == ver.minor
                                ):
                                    best_match = entry
                                    break
                            except Exception as e:
                                logger.error(f"Sync error 3: {e}")
                                pass
                        closest_cuda = best_match.supported_cuda
                        closest_rocm = best_match.supported_rocm

                    # Create and add the new entry
                    db.add(
                        PythonMatrixEntry(
                            id=uuid.uuid4(),
                            framework=framework,
                            version=v_str,
                            min_python=min_py,
                            max_python=max_py,
                            supported_cuda=closest_cuda,
                            supported_rocm=closest_rocm,
                            supported_python=supported_py,
                        )
                    )
                    new_entries += 1

                if new_entries > 0:
                    logger.info(
                        "Synced PyPI: Added %d new versions for %s",
                        new_entries,
                        framework,
                    )
                    await db.commit()
                    await clear_compatibility_cache()

            except Exception as exc:
                await db.rollback()
                logger.warning(
                    "Failed to sync PyPI releases for %s: %s", framework, exc
                )


async def sync_nvidia_cuda_releases(db: AsyncSession) -> None:
    """Fetch latest CUDA release toolkit information and append to DB."""
    url = "https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            if response.status_code != 200:
                logger.warning(
                    "Failed to fetch NVIDIA CUDA release notes: %s",
                    response.status_code,
                )
                return

            text = response.text
            # Regex to find CUDA versions like 12.6, 12.7, 12.8 in headings or text
            matches = re.findall(r"CUDA Toolkit\s+(\d+\.\d+)", text, re.IGNORECASE)
            if not matches:
                return

            db_result = await db.execute(select(CUDAMatrixEntry))
            existing_cuda = {e.cuda_version for e in db_result.scalars().all()}

            new_entries = 0
            for cuda_ver in set(matches):
                if cuda_ver in existing_cuda:
                    continue

                # Heuristic for new CUDA version driver requirements (based on latest existing version)
                db_prev = await db.execute(select(CUDAMatrixEntry))
                cuda_rows = db_prev.scalars().all()
                latest_existing = None
                if cuda_rows:
                    try:
                        latest_existing = max(
                            cuda_rows, key=lambda r: Version(r.cuda_version)
                        )
                    except Exception as e:
                        logger.error(f"Sync error 4: {e}")
                        latest_existing = cuda_rows[0]

                min_linux = (
                    latest_existing.min_driver_linux if latest_existing else "560.35.03"
                )
                min_win = (
                    latest_existing.min_driver_windows if latest_existing else "560.94"
                )
                cudnn = latest_existing.cudnn_versions if latest_existing else ["9.5.0"]
                archs = (
                    latest_existing.supported_archs
                    if latest_existing
                    else [
                        "sm_50",
                        "sm_60",
                        "sm_70",
                        "sm_75",
                        "sm_80",
                        "sm_86",
                        "sm_89",
                        "sm_90",
                    ]
                )

                db.add(
                    CUDAMatrixEntry(
                        id=uuid.uuid4(),
                        cuda_version=cuda_ver,
                        min_driver_linux=min_linux,
                        min_driver_windows=min_win,
                        cudnn_versions=cudnn,
                        supported_archs=archs,
                        notes=f"Automatically synced from NVIDIA release notes. Min driver inherited from CUDA {latest_existing.cuda_version if latest_existing else ''}.",
                        source_url=url,
                    )
                )
                new_entries += 1

            if new_entries > 0:
                logger.info("Synced NVIDIA: Added %d new CUDA versions", new_entries)
                await db.commit()
                await clear_compatibility_cache()

        except Exception as exc:
            await db.rollback()
            logger.warning("Failed to sync NVIDIA CUDA releases: %s", exc)


async def matrix_sync_loop(db_session_factory: Any) -> None:
    """Infinite loop task running sync operations once every 24 hours."""
    logger.info("Compatibility matrix syncing background task started.")
    while True:
        try:
            async with db_session_factory() as db:
                await sync_pypi_releases(db)
                await sync_nvidia_cuda_releases(db)
        except Exception as exc:
            logger.exception("Error in compatibility matrix sync loop: %s", exc)
        await asyncio.sleep(86400)
