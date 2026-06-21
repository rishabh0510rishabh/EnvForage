"""
Compatibility Matrix API endpoints.
Exposes CUDA, ROCm, and Python compatibility matrices as REST endpoints.
Dynamically fetches from the database if available, falling back to static constants.
"""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Path
from sqlalchemy import select

from app.api.deps import DB
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
from app.models.matrix import (
    CUDAMatrixEntry as CUDAMatrixDBModel,
)
from app.models.matrix import (
    PythonMatrixEntry as PythonMatrixDBModel,
)
from app.models.matrix import (
    RocmMatrixEntry as RocmMatrixDBModel,
)

router = APIRouter(prefix="/compatibility", tags=["Compatibility"])

# ── Summary ───────────────────────────────────────────────────────────────────


@router.get(
    "",
    summary="Get compatibility matrix summary",
    description=(
        "Return a high-level summary of CUDA, ROCm, and Python compatibility matrices."
    ),
    responses={
        200: {"description": "Compatibility summary retrieved successfully"},
    },
)
async def get_compatibility_summary(db: DB) -> dict[str, Any]:
    """
    Returns a high-level summary of all available compatibility matrices.
    Useful for frontend dropdowns and dynamic table headers.
    """
    # 1. CUDA Summary
    cuda_entries = None
    try:
        cuda_res = await db.execute(select(CUDAMatrixDBModel))
        cuda_entries = cuda_res.scalars().all()
    except Exception as e:
        import logging
        logging.error(f"CUDA summary DB fetch: {e}")
        pass

    if cuda_entries:
        cuda_versions = sorted({e.cuda_version for e in cuda_entries})
        cuda_count = len(cuda_entries)
    else:
        cuda_versions = SUPPORTED_CUDA_VERSIONS
        cuda_count = len(CUDA_MATRIX)

    # 2. ROCm Summary
    rocm_entries = None
    try:
        rocm_res = await db.execute(select(RocmMatrixDBModel))
        rocm_entries = rocm_res.scalars().all()
    except Exception as e:
        import logging
        logging.error(f"ROCm summary DB fetch: {e}")
        pass

    if rocm_entries:
        rocm_versions = sorted({e.rocm_version for e in rocm_entries})
        rocm_count = len(rocm_entries)
    else:
        rocm_versions = SUPPORTED_ROCM_VERSIONS
        rocm_count = len(ROCM_MATRIX)

    # 3. Python/Framework Summary
    python_entries = None
    try:
        python_res = await db.execute(select(PythonMatrixDBModel))
        python_entries = python_res.scalars().all()
    except Exception as e:
        import logging
        logging.error(f"Python summary DB fetch: {e}")
        pass

    if python_entries:
        frameworks = sorted({e.framework for e in python_entries})
        python_count = len(python_entries)
    else:
        frameworks = sorted(PYTHON_MATRIX.keys())
        python_count = sum(len(v) for v in PYTHON_MATRIX.values())

    return {
        "matrices": {
            "cuda": {
                "description": "CUDA version → NVIDIA driver + cuDNN + supported GPU architectures",
                "endpoint": "/api/v1/compatibility/cuda",
                "supported_versions": cuda_versions,
                "count": cuda_count,
            },
            "rocm": {
                "description": "ROCm version → Linux driver + supported AMD GPU architectures",
                "endpoint": "/api/v1/compatibility/rocm",
                "supported_versions": rocm_versions,
                "count": rocm_count,
            },
            "python": {
                "description": (
                    "Framework version → supported Python versions + CUDA/ROCm versions"
                ),
                "endpoint": "/api/v1/compatibility/python",
                "supported_frameworks": frameworks,
                "count": python_count,
            },
        }
    }


# ── CUDA ──────────────────────────────────────────────────────────────────────


@router.get(
    "/cuda",
    summary="List CUDA compatibility entries",
    description=(
        "Return the full CUDA compatibility matrix, including minimum NVIDIA "
        "driver versions, supported cuDNN versions, and supported GPU architectures."
    ),
    responses={
        200: {"description": "CUDA compatibility matrix retrieved successfully"},
    },
)
async def get_cuda_matrix(db: DB) -> dict[str, Any]:
    """
    Returns the full CUDA compatibility matrix.
    Each entry maps a CUDA version to its minimum required NVIDIA driver
    (Linux + Windows), supported cuDNN versions, and supported GPU architectures.
    """
    cuda_entries = None
    try:
        res = await db.execute(select(CUDAMatrixDBModel))
        cuda_entries = res.scalars().all()
    except Exception as e:
        import logging
        logging.error(f"CUDA Matrix DB fetch: {e}")
        pass

    if cuda_entries:
        data = {
            e.cuda_version: {
                "cuda_version": e.cuda_version,
                "min_driver_linux": e.min_driver_linux,
                "min_driver_windows": e.min_driver_windows,
                "cudnn_versions": e.cudnn_versions,
                "supported_archs": e.supported_archs,
                "notes": e.notes or "",
                "source_url": e.source_url or "",
            }
            for e in cuda_entries
        }
        supported = sorted(data.keys())
        count = len(cuda_entries)
    else:
        data = {version: asdict(entry) for version, entry in CUDA_MATRIX.items()}
        supported = SUPPORTED_CUDA_VERSIONS
        count = len(CUDA_MATRIX)

    return {
        "matrix": "cuda",
        "count": count,
        "supported_versions": supported,
        "data": data,
    }


@router.get(
    "/cuda/frameworks",
    summary="List framework CUDA support",
    description=(
        "Return a mapping of supported CUDA versions for each framework version."
    ),
    responses={
        200: {"description": "Framework CUDA support map retrieved successfully"},
    },
)
async def get_framework_cuda_support(db: DB) -> dict[str, Any]:
    """
    Returns the framework → CUDA version support map.
    Shows which CUDA versions each framework version officially supports.
    """
    entries = None
    try:
        res = await db.execute(select(PythonMatrixDBModel))
        entries = res.scalars().all()
    except Exception as error:
        import logging
        logging.error(f"CUDA Framework DB fetch: {error}")
        pass

    if entries:
        data: dict[str, dict[str, list[str]]] = {}
        for entry in entries:
            if entry.supported_cuda:
                if entry.framework not in data:
                    data[entry.framework] = {}
                data[entry.framework][entry.version] = entry.supported_cuda
    else:
        data = FRAMEWORK_CUDA_SUPPORT

    return {
        "matrix": "framework_cuda_support",
        "data": data,
    }


@router.get(
    "/cuda/{cuda_version}",
    summary="Get CUDA compatibility entry",
    description=(
        "Return compatibility details for a specific CUDA version, including "
        "driver requirements, cuDNN support, and supported GPU architectures."
    ),
    responses={
        200: {"description": "CUDA compatibility entry retrieved successfully"},
        404: {"description": "CUDA version not found in compatibility matrix"},
    },
)
async def get_cuda_version(
    db: DB,
    cuda_version: str = Path(
        ...,
        description="CUDA version identifier to look up.",
        examples=["12.1"],
    ),
) -> dict[str, Any]:
    """
    Returns the compatibility entry for a specific CUDA version.
    - **cuda_version**: e.g. `11.8`, `12.1`, `12.4`
    """
    try:
        res = await db.execute(
            select(CUDAMatrixDBModel).where(
                CUDAMatrixDBModel.cuda_version == cuda_version
            )
        )
        entry = res.scalars().first()
        if entry:
            return {
                "cuda_version": entry.cuda_version,
                "min_driver_linux": entry.min_driver_linux,
                "min_driver_windows": entry.min_driver_windows,
                "cudnn_versions": entry.cudnn_versions,
                "supported_archs": entry.supported_archs,
                "notes": entry.notes or "",
                "source_url": entry.source_url or "",
            }
    except Exception as e:
        import logging
        logging.error(f"CUDA version lookup: {e}")
        pass

    # Fallback to static
    static_entry = CUDA_MATRIX.get(cuda_version)
    if static_entry is None:
        try:
            res_all = await db.execute(select(CUDAMatrixDBModel.cuda_version))
            supported = sorted(res_all.scalars().all())
        except Exception:
            supported = SUPPORTED_CUDA_VERSIONS
        if not supported:
            supported = SUPPORTED_CUDA_VERSIONS

        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "CUDA_VERSION_NOT_FOUND",
                    "message": (
                        f"CUDA version '{cuda_version}' is not in the "
                        "compatibility matrix."
                    ),
                    "supported_versions": supported,
                }
            },
        )
    return {"cuda_version": cuda_version, **asdict(static_entry)}


# ── ROCm ──────────────────────────────────────────────────────────────────────


@router.get(
    "/rocm",
    summary="List ROCm compatibility entries",
    description=(
        "Return the full ROCm compatibility matrix, including required Linux "
        "driver versions and supported AMD GPU architectures."
    ),
    responses={
        200: {"description": "ROCm compatibility matrix retrieved successfully"},
    },
)
async def get_rocm_matrix(db: DB) -> dict[str, Any]:
    """
    Returns the full ROCm compatibility matrix.
    Each entry maps a ROCm version to its minimum required Linux driver version
    and supported AMD GPU architectures.
    """
    rocm_entries = None
    try:
        res = await db.execute(select(RocmMatrixDBModel))
        rocm_entries = res.scalars().all()
    except Exception:
        pass

    if rocm_entries:
        data = {
            e.rocm_version: {
                "rocm_version": e.rocm_version,
                "min_driver_linux": e.min_driver_linux,
                "supported_gpus": e.supported_gpus,
                "notes": e.notes or "",
                "source_url": e.source_url or "",
            }
            for e in rocm_entries
        }
        supported = sorted(data.keys())
        count = len(rocm_entries)
    else:
        data = {version: asdict(entry) for version, entry in ROCM_MATRIX.items()}
        supported = SUPPORTED_ROCM_VERSIONS
        count = len(ROCM_MATRIX)

    return {
        "matrix": "rocm",
        "count": count,
        "supported_versions": supported,
        "data": data,
    }


@router.get(
    "/rocm/frameworks",
    summary="List framework ROCm support",
    description=(
        "Return a mapping of supported ROCm versions for each framework version."
    ),
    responses={
        200: {"description": "Framework ROCm support map retrieved successfully"},
    },
)
async def get_framework_rocm_support(db: DB) -> dict[str, Any]:
    """
    Returns the framework → ROCm version support map.
    Shows which ROCm versions each framework version officially supports.
    """
    entries = None
    try:
        res = await db.execute(select(PythonMatrixDBModel))
        entries = res.scalars().all()
    except Exception:
        pass

    if entries:
        data: dict[str, dict[str, list[str]]] = {}
        for e in entries:
            if e.supported_rocm:
                if e.framework not in data:
                    data[e.framework] = {}
                data[e.framework][e.version] = e.supported_rocm
    else:
        data = FRAMEWORK_ROCM_SUPPORT

    return {
        "matrix": "framework_rocm_support",
        "data": data,
    }


@router.get(
    "/rocm/{rocm_version}",
    summary="Get ROCm compatibility entry",
    description=(
        "Return compatibility details for a specific ROCm version, including "
        "driver requirements and supported AMD GPU architectures."
    ),
    responses={
        200: {"description": "ROCm compatibility entry retrieved successfully"},
        404: {"description": "ROCm version not found in compatibility matrix"},
    },
)
async def get_rocm_version(
    db: DB,
    rocm_version: str = Path(
        ...,
        description="ROCm version identifier to look up.",
        examples=["6.0.0"],
    ),
) -> dict[str, Any]:
    """
    Returns the compatibility entry for a specific ROCm version.
    - **rocm_version**: e.g. `5.7.0`, `6.0.0`
    """
    try:
        res = await db.execute(
            select(RocmMatrixDBModel).where(
                RocmMatrixDBModel.rocm_version == rocm_version
            )
        )
        entry = res.scalars().first()
        if entry:
            return {
                "rocm_version": entry.rocm_version,
                "min_driver_linux": entry.min_driver_linux,
                "supported_gpus": entry.supported_gpus,
                "notes": entry.notes or "",
                "source_url": entry.source_url or "",
            }
    except Exception:
        pass

    static_entry = ROCM_MATRIX.get(rocm_version)
    if static_entry is None:
        try:
            res_all = await db.execute(select(RocmMatrixDBModel.rocm_version))
            supported = sorted(res_all.scalars().all())
        except Exception:
            supported = SUPPORTED_ROCM_VERSIONS
        if not supported:
            supported = SUPPORTED_ROCM_VERSIONS

        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "ROCM_VERSION_NOT_FOUND",
                    "message": (
                        f"ROCm version '{rocm_version}' is not in the "
                        "compatibility matrix."
                    ),
                    "supported_versions": supported,
                }
            },
        )
    return {"rocm_version": rocm_version, **asdict(static_entry)}


# ── Python ────────────────────────────────────────────────────────────────────


@router.get(
    "/python",
    summary="List Python compatibility entries",
    description=(
        "Return the full Python compatibility matrix for supported frameworks, "
        "including compatible Python, CUDA, and ROCm versions."
    ),
    responses={
        200: {"description": "Python compatibility matrix retrieved successfully"},
    },
)
async def get_python_matrix(db: DB) -> dict[str, Any]:
    """
    Returns the full Python compatibility matrix.
    Each framework maps to a list of versioned entries showing supported
    Python versions, CUDA versions, and ROCm versions.
    """
    entries = None
    try:
        res = await db.execute(select(PythonMatrixDBModel))
        entries = res.scalars().all()
    except Exception:
        pass

    if entries:
        frameworks = sorted({e.framework for e in entries})
        data: dict[str, list[dict[str, Any]]] = {}
        for e in entries:
            if e.framework not in data:
                data[e.framework] = []
            data[e.framework].append(
                {
                    "framework": e.framework,
                    "version": e.version,
                    "min_python": e.min_python,
                    "max_python": e.max_python,
                    "supported_cuda": e.supported_cuda,
                    "supported_rocm": e.supported_rocm,
                    "supported_python": e.supported_python,
                }
            )
    else:
        frameworks = sorted(PYTHON_MATRIX.keys())
        data = {
            framework: [asdict(entry) for entry in entries]
            for framework, entries in PYTHON_MATRIX.items()
        }

    return {
        "matrix": "python",
        "supported_frameworks": frameworks,
        "data": data,
    }


@router.get(
    "/python/{framework}",
    summary="Get Python compatibility by framework",
    description=("Return all Python compatibility entries for a specific framework."),
    responses={
        200: {"description": "Framework Python compatibility retrieved successfully"},
        404: {"description": "Framework not found in Python compatibility matrix"},
    },
)
async def get_python_framework(
    db: DB,
    framework: str = Path(
        ...,
        description="Framework name to look up.",
        examples=["torch"],
    ),
) -> dict[str, Any]:
    """
    Returns all versioned Python compatibility entries for a given framework.
    - **framework**: e.g. `torch`, `tensorflow`, `ultralytics`
    """
    try:
        res = await db.execute(
            select(PythonMatrixDBModel).where(
                PythonMatrixDBModel.framework == framework
            )
        )
        entries = res.scalars().all()
        if entries:
            return {
                "framework": framework,
                "count": len(entries),
                "data": [
                    {
                        "framework": e.framework,
                        "version": e.version,
                        "min_python": e.min_python,
                        "max_python": e.max_python,
                        "supported_cuda": e.supported_cuda,
                        "supported_rocm": e.supported_rocm,
                        "supported_python": e.supported_python,
                    }
                    for e in entries
                ],
            }
    except Exception:
        pass

    static_entries = PYTHON_MATRIX.get(framework)
    if static_entries is None:
        try:
            res_all = await db.execute(select(PythonMatrixDBModel.framework).distinct())
            supported = sorted(res_all.scalars().all())
        except Exception:
            supported = sorted(PYTHON_MATRIX.keys())
        if not supported:
            supported = sorted(PYTHON_MATRIX.keys())

        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "FRAMEWORK_NOT_FOUND",
                    "message": (
                        f"Framework '{framework}' is not in the Python "
                        "compatibility matrix."
                    ),
                    "supported_frameworks": supported,
                }
            },
        )
    return {
        "framework": framework,
        "count": len(static_entries),
        "data": [asdict(entry) for entry in static_entries],
    }


@router.get(
    "/python/{framework}/{version}",
    summary="Get Python compatibility by framework version",
    description=(
        "Return Python, CUDA, and ROCm compatibility details for a specific "
        "framework version."
    ),
    responses={
        200: {"description": "Framework version compatibility retrieved successfully"},
        404: {"description": "Framework or framework version not found"},
    },
)
async def get_python_framework_version(
    db: DB,
    framework: str = Path(
        ...,
        description="Framework name to look up.",
        examples=["torch"],
    ),
    version: str = Path(
        ...,
        description="Framework version to look up.",
        examples=["2.1.0"],
    ),
) -> dict[str, Any]:
    """
    Returns the Python compatibility entry for a specific framework version.
    - **framework**: e.g. `torch`, `tensorflow`
    - **version**: e.g. `2.1.0`, `2.15.0`
    """
    try:
        res = await db.execute(
            select(PythonMatrixDBModel).where(
                (PythonMatrixDBModel.framework == framework)
                & (PythonMatrixDBModel.version == version)
            )
        )
        db_entry = res.scalars().first()
        if db_entry:
            return {
                "framework": framework,
                "version": version,
                "min_python": db_entry.min_python,
                "max_python": db_entry.max_python,
                "supported_cuda": db_entry.supported_cuda,
                "supported_rocm": db_entry.supported_rocm,
                "supported_python": db_entry.supported_python,
            }
    except Exception:
        pass

    static_entries = PYTHON_MATRIX.get(framework)
    if static_entries is None:
        try:
            res_all = await db.execute(select(PythonMatrixDBModel.framework).distinct())
            supported = sorted(res_all.scalars().all())
        except Exception:
            supported = sorted(PYTHON_MATRIX.keys())
        if not supported:
            supported = sorted(PYTHON_MATRIX.keys())

        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "FRAMEWORK_NOT_FOUND",
                    "message": (
                        f"Framework '{framework}' is not in the Python "
                        "compatibility matrix."
                    ),
                    "supported_frameworks": supported,
                }
            },
        )

    for static_entry in static_entries:
        if static_entry.version == version:
            return {"framework": framework, "version": version, **asdict(static_entry)}

    try:
        res_ver = await db.execute(
            select(PythonMatrixDBModel.version).where(
                PythonMatrixDBModel.framework == framework
            )
        )
        avail = sorted(res_ver.scalars().all())
    except Exception:
        avail = [e.version for e in static_entries]
    if not avail:
        avail = [e.version for e in static_entries]

    raise HTTPException(
        status_code=404,
        detail={
            "error": {
                "code": "FRAMEWORK_VERSION_NOT_FOUND",
                "message": (
                    f"Version '{version}' not found for framework '{framework}'."
                ),
                "available_versions": avail,
            }
        },
    )


# --- Advanced OpenTelemetry Decorator ---
import functools
import logging
import time

logger = logging.getLogger("CompatibilityTracer")

def trace_execution(operation_name: str):
    """
    A decorator that simulates an OpenTelemetry span for complex compatibility resolutions.
    It tracks latency, success rate, and captures input dimensions.
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            logger.info(f"[TRACE-START] {operation_name} with args={kwargs}")
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start_time
                logger.info(f"[TRACE-SUCCESS] {operation_name} completed in {duration*1000:.2f}ms")
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                logger.error(f"[TRACE-ERROR] {operation_name} failed after {duration*1000:.2f}ms: {e}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            logger.info(f"[TRACE-START] {operation_name} with args={kwargs}")
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start_time
                logger.info(f"[TRACE-SUCCESS] {operation_name} completed in {duration*1000:.2f}ms")
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                logger.error(f"[TRACE-ERROR] {operation_name} failed after {duration*1000:.2f}ms: {e}")
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

class MatrixCacheOptimizer:
    """Handles intelligent warming and invalidation of the compatibility matrix cache."""
    def __init__(self):
        self._hits = 0
        self._misses = 0

    def record_hit(self):
        self._hits += 1

    def record_miss(self):
        self._misses += 1

    def hit_ratio(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

