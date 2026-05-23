"""
Compatibility Matrix API endpoints.
Exposes CUDA, ROCm, and Python compatibility matrices as read-only REST endpoints.
Resolves Issue #85.
"""
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException

from app.compatibility.matrix.cuda import (
    CUDA_MATRIX,
    FRAMEWORK_CUDA_SUPPORT,
    SUPPORTED_CUDA_VERSIONS,
)
from app.compatibility.matrix.python import PYTHON_MATRIX
from app.compatibility.matrix.rocm import (
    FRAMEWORK_ROCM_SUPPORT,
    ROCM_MATRIX,
    SUPPORTED_ROCM_VERSIONS,
)

router = APIRouter(prefix="/compatibility")

# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("", summary="Summary of all compatibility matrices")
async def get_compatibility_summary() -> dict[str, Any]:
    """
    Returns a high-level summary of all available compatibility matrices.
    Useful for frontend dropdowns and dynamic table headers.
    """
    return {
        "matrices": {
            "cuda": {
                "description": "CUDA version → NVIDIA driver + cuDNN + supported GPU architectures",
                "endpoint": "/api/v1/compatibility/cuda",
                "supported_versions": SUPPORTED_CUDA_VERSIONS,
                "count": len(CUDA_MATRIX),
            },
            "rocm": {
                "description": "ROCm version → Linux driver + supported AMD GPU architectures",
                "endpoint": "/api/v1/compatibility/rocm",
                "supported_versions": SUPPORTED_ROCM_VERSIONS,
                "count": len(ROCM_MATRIX),
            },
            "python": {
                "description": "Framework version → supported Python versions + CUDA/ROCm versions",
                "endpoint": "/api/v1/compatibility/python",
                "supported_frameworks": sorted(PYTHON_MATRIX.keys()),
                "count": sum(len(v) for v in PYTHON_MATRIX.values()),
            },
        }
    }

# ── CUDA ──────────────────────────────────────────────────────────────────────

@router.get("/cuda", summary="List all CUDA compatibility entries")
async def get_cuda_matrix() -> dict[str, Any]:
    """
    Returns the full CUDA compatibility matrix.
    Each entry maps a CUDA version to its minimum required NVIDIA driver
    (Linux + Windows), supported cuDNN versions, and supported GPU architectures.
    """
    return {
        "matrix": "cuda",
        "count": len(CUDA_MATRIX),
        "supported_versions": SUPPORTED_CUDA_VERSIONS,
        "data": {version: asdict(entry) for version, entry in CUDA_MATRIX.items()},
    }

@router.get("/cuda/frameworks", summary="List framework → CUDA version support map")
async def get_framework_cuda_support() -> dict[str, Any]:
    """
    Returns the framework → CUDA version support map.
    Shows which CUDA versions each framework version officially supports.
    """
    return {
        "matrix": "framework_cuda_support",
        "data": FRAMEWORK_CUDA_SUPPORT,
    }

@router.get("/cuda/{cuda_version}", summary="Get a single CUDA version entry")
async def get_cuda_version(cuda_version: str) -> dict[str, Any]:
    """
    Returns the compatibility entry for a specific CUDA version.
    - **cuda_version**: e.g. `11.8`, `12.1`, `12.4`
    """
    entry = CUDA_MATRIX.get(cuda_version)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "CUDA_VERSION_NOT_FOUND",
                    "message": f"CUDA version '{cuda_version}' is not in the compatibility matrix.",
                    "supported_versions": SUPPORTED_CUDA_VERSIONS,
                }
            },
        )
    return {"cuda_version": cuda_version, **asdict(entry)}

# ── ROCm ──────────────────────────────────────────────────────────────────────

@router.get("/rocm", summary="List all ROCm compatibility entries")
async def get_rocm_matrix() -> dict[str, Any]:
    """
    Returns the full ROCm compatibility matrix.
    Each entry maps a ROCm version to its minimum required Linux driver version
    and supported AMD GPU architectures.
    """
    return {
        "matrix": "rocm",
        "count": len(ROCM_MATRIX),
        "supported_versions": SUPPORTED_ROCM_VERSIONS,
        "data": {version: asdict(entry) for version, entry in ROCM_MATRIX.items()},
    }

@router.get("/rocm/frameworks", summary="List framework → ROCm version support map")
async def get_framework_rocm_support() -> dict[str, Any]:
    """
    Returns the framework → ROCm version support map.
    Shows which ROCm versions each framework version officially supports.
    """
    return {
        "matrix": "framework_rocm_support",
        "data": FRAMEWORK_ROCM_SUPPORT,
    }

@router.get("/rocm/{rocm_version}", summary="Get a single ROCm version entry")
async def get_rocm_version(rocm_version: str) -> dict[str, Any]:
    """
    Returns the compatibility entry for a specific ROCm version.
    - **rocm_version**: e.g. `5.7.0`, `6.0.0`
    """
    entry = ROCM_MATRIX.get(rocm_version)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "ROCM_VERSION_NOT_FOUND",
                    "message": f"ROCm version '{rocm_version}' is not in the compatibility matrix.",
                    "supported_versions": SUPPORTED_ROCM_VERSIONS,
                }
            },
        )
    return {"rocm_version": rocm_version, **asdict(entry)}

# ── Python ────────────────────────────────────────────────────────────────────

@router.get("/python", summary="List all Python compatibility entries")
async def get_python_matrix() -> dict[str, Any]:
    """
    Returns the full Python compatibility matrix.
    Each framework maps to a list of versioned entries showing supported
    Python versions, CUDA versions, and ROCm versions.
    """
    return {
        "matrix": "python",
        "supported_frameworks": sorted(PYTHON_MATRIX.keys()),
        "data": {
            framework: [asdict(entry) for entry in entries]
            for framework, entries in PYTHON_MATRIX.items()
        },
    }

@router.get("/python/{framework}", summary="Get Python compatibility for a specific framework")
async def get_python_framework(framework: str) -> dict[str, Any]:
    """
    Returns all versioned Python compatibility entries for a given framework.
    - **framework**: e.g. `torch`, `tensorflow`, `ultralytics`
    """
    entries = PYTHON_MATRIX.get(framework)
    if entries is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "FRAMEWORK_NOT_FOUND",
                    "message": f"Framework '{framework}' is not in the Python compatibility matrix.",
                    "supported_frameworks": sorted(PYTHON_MATRIX.keys()),
                }
            },
        )
    return {
        "framework": framework,
        "count": len(entries),
        "data": [asdict(entry) for entry in entries],
    }

@router.get("/python/{framework}/{version}", summary="Get Python compatibility for a specific framework version")
async def get_python_framework_version(framework: str, version: str) -> dict[str, Any]:
    """
    Returns the Python compatibility entry for a specific framework version.
    - **framework**: e.g. `torch`, `tensorflow`
    - **version**: e.g. `2.1.0`, `2.15.0`
    """
    entries = PYTHON_MATRIX.get(framework)
    if entries is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "FRAMEWORK_NOT_FOUND",
                    "message": f"Framework '{framework}' is not in the Python compatibility matrix.",
                    "supported_frameworks": sorted(PYTHON_MATRIX.keys()),
                }
            },
        )
    for entry in entries:
        if entry.version == version:
            return {"framework": framework, "version": version, **asdict(entry)}
    raise HTTPException(
        status_code=404,
        detail={
            "error": {
                "code": "FRAMEWORK_VERSION_NOT_FOUND",
                "message": f"Version '{version}' not found for framework '{framework}'.",
                "available_versions": [e.version for e in entries],
            }
        },
    )
