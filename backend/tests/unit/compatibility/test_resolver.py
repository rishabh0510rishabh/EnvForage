"""
Unit tests for the Compatibility Resolver.
No mocks for matrix data — the matrix IS the ground truth.
"""

import inspect

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.compatibility.errors import (
    IncompatibilityError,
    UnknownVersionError,
    UnsupportedOSError,
)
from app.compatibility.matrix.cuda import CUDA_MATRIX
from app.compatibility.matrix.python import PYTHON_MATRIX
from app.compatibility.models import PackageConstraint
from app.compatibility.resolver import CompatibilityResolver

pytestmark = pytest.mark.asyncio

R = CompatibilityResolver()

KNOWN_FRAMEWORK_VERSIONS = [
    (framework, entry.version)
    for framework, entries in PYTHON_MATRIX.items()
    for entry in entries
]
VERSION_STRINGS = st.one_of(
    st.sampled_from(["3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]),
    st.from_regex(r"\d{1,2}\.\d{1,2}(?:\.\d{1,2})?", fullmatch=True),
    st.sampled_from(["", "latest", "cu118", "12.x", "3.11-dev"]),
)
PACKAGE_CONSTRAINTS = st.one_of(
    st.sampled_from(KNOWN_FRAMEWORK_VERSIONS).map(
        lambda package: PackageConstraint(package[0], package[1])
    ),
    st.builds(
        PackageConstraint,
        name=st.sampled_from(["torch", "tensorflow", "jax", "ultralytics"]),
        version_spec=VERSION_STRINGS,
    ),
    st.builds(
        PackageConstraint,
        name=st.sampled_from(["matplotlib", "numpy", "scikit-learn"]),
        version_spec=VERSION_STRINGS,
    ),
)


async def _await_if_needed(value):
    if inspect.isawaitable(value):
        return await value
    return value


@settings(max_examples=1000, deadline=None)
@given(
    packages=st.lists(PACKAGE_CONSTRAINTS, min_size=0, max_size=4),
    python_version=VERSION_STRINGS,
    cuda_version=st.one_of(
        st.none(), st.sampled_from(list(CUDA_MATRIX)), VERSION_STRINGS
    ),
    target_os=st.sampled_from(["LINUX", "WSL", "WIN"]),
    cuda_required=st.booleans(),
)
async def test_resolve_handles_generated_version_inputs(
    packages,
    python_version,
    cuda_version,
    target_os,
    cuda_required,
):
    """Generated inputs either resolve or fail with a structured compatibility error."""
    try:
        result = await R.resolve(
            packages=packages,
            python_version=python_version,
            cuda_version=cuda_version,
            target_os=target_os,
            profile_slug="generated-profile",
            os_support=["LINUX", "WSL", "WIN"],
            cuda_required=cuda_required,
        )
    except (IncompatibilityError, UnknownVersionError, UnsupportedOSError):
        return

    assert result.python_version == python_version
    assert result.cuda_version == cuda_version
    assert result.target_os == target_os
    assert len(result.packages) == len(packages)


async def test_resolve_pytorch_cuda118_py311():
    result = await R.resolve(
        packages=[PackageConstraint("torch", "2.1.2")],
        python_version="3.11",
        cuda_version="11.8",
        target_os="LINUX",
        profile_slug="pytorch-cuda",
        os_support=["LINUX", "WSL"],
        cuda_required=True,
    )
    assert result.packages[0].version == "2.1.2"
    assert result.packages[0].cuda_variant == "cu118"


async def test_resolve_cpu_only():
    result = await R.resolve(
        packages=[PackageConstraint("opencv-python", "4.9.0.80")],
        python_version="3.11",
        cuda_version=None,
        target_os="WIN",
        profile_slug="opencv-beginner",
        os_support=["LINUX", "WSL", "WIN"],
        cuda_required=False,
    )
    assert result.cuda_version is None
    assert result.packages[0].cuda_variant is None


async def test_wsl_note_in_warnings():
    result = await R.resolve(
        packages=[PackageConstraint("torch", "2.1.0")],
        python_version="3.10",
        cuda_version="11.8",
        target_os="WSL",
        profile_slug="pytorch-cuda",
        os_support=["LINUX", "WSL"],
        cuda_required=True,
    )
    assert any("WSL" in w for w in result.warnings)


async def test_version_override():
    result = await R.resolve(
        packages=[PackageConstraint("torch", "2.1.2")],
        python_version="3.11",
        cuda_version="11.8",
        target_os="LINUX",
        profile_slug="pytorch-cuda",
        os_support=["LINUX", "WSL"],
        cuda_required=True,
        overrides={"torch": "2.2.2"},
    )
    assert result.packages[0].version == "2.2.2"


async def test_unsupported_os_raises():
    with pytest.raises(UnsupportedOSError) as exc:
        await R.resolve(
            packages=[PackageConstraint("torch", "2.1.0")],
            python_version="3.11",
            cuda_version="11.8",
            target_os="WIN",
            profile_slug="pytorch-cuda",
            os_support=["LINUX", "WSL"],
            cuda_required=True,
        )
    assert exc.value.requested_os == "WIN"


async def test_unknown_cuda_raises():
    with pytest.raises(UnknownVersionError) as exc:
        await R.resolve(
            packages=[PackageConstraint("torch", "2.1.0")],
            python_version="3.11",
            cuda_version="10.2",
            target_os="LINUX",
            profile_slug="pytorch-cuda",
            os_support=["LINUX", "WSL"],
            cuda_required=True,
        )
    assert exc.value.version == "10.2"


async def test_python_mismatch_raises():
    with pytest.raises(IncompatibilityError) as exc:
        await R.resolve(
            packages=[PackageConstraint("torch", "2.1.0")],
            python_version="3.7",
            cuda_version="11.8",
            target_os="LINUX",
            profile_slug="pytorch-cuda",
            os_support=["LINUX", "WSL"],
            cuda_required=True,
        )
    assert exc.value.component == "python"


async def test_cuda_required_without_version_raises():
    with pytest.raises(IncompatibilityError) as exc:
        await R.resolve(
            packages=[PackageConstraint("torch", "2.1.0")],
            python_version="3.11",
            cuda_version=None,
            target_os="LINUX",
            profile_slug="pytorch-cuda",
            os_support=["LINUX", "WSL"],
            cuda_required=True,
        )
    assert exc.value.component == "cuda"


async def test_cuda_version_mismatch_raises():
    with pytest.raises(IncompatibilityError) as exc:
        await R.resolve(
            packages=[PackageConstraint("torch", "2.1.0")],
            python_version="3.11",
            cuda_version="12.4",
            target_os="LINUX",
            profile_slug="pytorch-cuda",
            os_support=["LINUX", "WSL"],
            cuda_required=True,
        )
    assert exc.value.component == "cuda"


async def test_non_matrix_package_uses_spec():
    result = await R.resolve(
        packages=[PackageConstraint("matplotlib", "3.8.4")],
        python_version="3.11",
        cuda_version=None,
        target_os="LINUX",
        profile_slug="opencv-beginner",
        os_support=["LINUX", "WIN", "WSL"],
        cuda_required=False,
    )
    assert result.packages[0].version == "3.8.4"


@pytest.mark.asyncio
async def test_warns_on_hybrid_conda_pip_gpu_environment():
    result = await _await_if_needed(
        R.resolve(
            packages=[
                PackageConstraint("numpy", "1.26.4"),
                PackageConstraint("torch", "2.1.2", cuda_variant="cu118"),
            ],
            python_version="3.11",
            cuda_version="11.8",
            target_os="LINUX",
            profile_slug="pytorch-cuda",
            os_support=["LINUX", "WSL"],
            cuda_required=True,
        )
    )
    assert any(
        "conda-managed packages" in warning and "ABI-sensitive" in warning
        for warning in result.warnings
    )


@pytest.mark.asyncio
async def test_to_dict_serializes():
    result = await _await_if_needed(
        R.resolve(
            packages=[PackageConstraint("torch", "2.1.0")],
            python_version="3.11",
            cuda_version="11.8",
            target_os="LINUX",
            profile_slug="pytorch-cuda",
            os_support=["LINUX", "WSL"],
            cuda_required=True,
        )
    )
    d = result.to_dict()
    assert d["python_version"] == "3.11"
    assert isinstance(d["packages"], list)


# ── JAX CUDA Support Matrix Tests ─────────────────────────────────────────────


def test_jax_cuda118_supported():
    """JAX 0.4.14 supports only CUDA 11.8."""
    from app.compatibility.matrix.cuda import get_supported_cuda_for_framework

    cuda_versions = get_supported_cuda_for_framework("jax", "0.4.14")
    assert set(cuda_versions) == {"11.8"}


def test_jax_cuda121_supported():
    """JAX 0.4.28 supports CUDA 12.1 and 12.4."""
    from app.compatibility.matrix.cuda import get_supported_cuda_for_framework

    cuda_versions = get_supported_cuda_for_framework("jax", "0.4.28")
    assert set(cuda_versions) == {"12.1", "12.4"}


def test_jax_cuda124_supported():
    """JAX 0.4.28 supports CUDA 12.1 and 12.4."""
    from app.compatibility.matrix.cuda import get_supported_cuda_for_framework

    cuda_versions = get_supported_cuda_for_framework("jax", "0.4.28")
    assert set(cuda_versions) == {"12.1", "12.4"}


def test_jax_cuda118_dropped_in_0426():
    """JAX 0.4.26 supports only CUDA 12.1, not 11.8."""
    from app.compatibility.matrix.cuda import get_supported_cuda_for_framework

    cuda_versions = get_supported_cuda_for_framework("jax", "0.4.26")
    assert set(cuda_versions) == {"12.1"}


def test_jax_unknown_version_returns_empty():
    """Unknown JAX version should return empty list, not crash."""
    from app.compatibility.matrix.cuda import get_supported_cuda_for_framework

    cuda_versions = get_supported_cuda_for_framework("jax", "0.0.0")
    assert cuda_versions == []


def test_cuda_125_in_matrix():
    """CUDA 12.5 must be recognized in the matrix."""
    from app.compatibility.matrix.cuda import get_cuda_entry

    entry = get_cuda_entry("12.5")
    assert entry is not None
    assert entry.min_driver_linux == "555.42.02"
    assert entry.min_driver_windows == "555.85"


def test_cuda_126_in_matrix():
    """CUDA 12.6 must be recognized in the matrix."""
    from app.compatibility.matrix.cuda import get_cuda_entry

    entry = get_cuda_entry("12.6")
    assert entry is not None
    assert entry.min_driver_linux == "560.35.03"
    assert entry.min_driver_windows == "560.94"


def test_cuda_125_126_in_supported_versions():
    """12.5 and 12.6 must appear in SUPPORTED_CUDA_VERSIONS."""
    from app.compatibility.matrix.cuda import SUPPORTED_CUDA_VERSIONS

    assert "12.5" in SUPPORTED_CUDA_VERSIONS
    assert "12.6" in SUPPORTED_CUDA_VERSIONS


async def test_rocm_version_override_success():
    result = await R.resolve(
        packages=[PackageConstraint("torch", "2.0.0")],
        python_version="3.10",
        cuda_version=None,
        rocm_version="5.6.0",
        target_os="LINUX",
        profile_slug="pytorch-rocm",
        os_support=["LINUX"],
        rocm_required=True,
        overrides={"torch": "2.1.0"},
    )
    assert result.packages[0].version == "2.1.0"
    assert result.packages[0].cuda_variant == "rocm5.6.0"


async def test_rocm_version_override_failure():
    with pytest.raises(IncompatibilityError) as exc:
        await R.resolve(
            packages=[PackageConstraint("torch", "2.1.0")],
            python_version="3.10",
            cuda_version=None,
            rocm_version="5.6.0",
            target_os="LINUX",
            profile_slug="pytorch-rocm",
            os_support=["LINUX"],
            rocm_required=True,
            overrides={"torch": "2.4.0"},  # 2.4.0 only supports ROCm 6.0.0
        )
    assert exc.value.component == "rocm"


async def test_semver_range_resolution():
    result = await R.resolve(
        packages=[PackageConstraint("torch", ">=2.0.0,<2.3.0")],
        python_version="3.11",
        cuda_version="11.8",
        target_os="LINUX",
        profile_slug="pytorch-cuda",
        os_support=["LINUX", "WSL"],
        cuda_required=True,
    )

    assert result.packages[0].version == "2.2.2"


async def test_wildcard_version_resolution():
    result = await R.resolve(
        packages=[PackageConstraint("torch", "==2.1.*")],
        python_version="3.11",
        cuda_version="11.8",
        target_os="LINUX",
        profile_slug="pytorch-cuda",
        os_support=["LINUX", "WSL"],
        cuda_required=True,
    )

    assert result.packages[0].version == "2.1.2"


async def test_compatible_release_resolution():
    result = await R.resolve(
        packages=[PackageConstraint("torch", "~=2.1")],
        python_version="3.11",
        cuda_version="11.8",
        target_os="LINUX",
        profile_slug="pytorch-cuda",
        os_support=["LINUX", "WSL"],
        cuda_required=True,
    )

    assert result.packages[0].version == "2.5.0"


async def test_invalid_semver_specifier():
    with pytest.raises(IncompatibilityError):
        await R.resolve(
            packages=[PackageConstraint("torch", ">>>invalid<<<")],
            python_version="3.11",
            cuda_version="11.8",
            target_os="LINUX",
            profile_slug="pytorch-cuda",
            os_support=["LINUX", "WSL"],
            cuda_required=True,
        )


async def test_no_matching_semver_range():
    with pytest.raises(IncompatibilityError):
        await R.resolve(
            packages=[PackageConstraint("torch", ">=99.0.0")],
            python_version="3.11",
            cuda_version="11.8",
            target_os="LINUX",
            profile_slug="pytorch-cuda",
            os_support=["LINUX", "WSL"],
            cuda_required=True,
        )
