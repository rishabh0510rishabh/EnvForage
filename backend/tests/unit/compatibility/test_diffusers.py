"""
Unit tests for the Hugging Face Diffusers environment profile.
Tests the Python compatibility matrix, CUDA support map, and resolver integration.
"""

import pytest

from app.compatibility.errors import IncompatibilityError
from app.compatibility.matrix.cuda import get_supported_cuda_for_framework
from app.compatibility.matrix.python import (
    PYTHON_MATRIX,
    get_framework_entry,
    get_framework_versions,
    get_latest_compatible_version,
)
from app.compatibility.models import PackageConstraint
from app.compatibility.resolver import CompatibilityResolver

R = CompatibilityResolver()

# ── Python Matrix Tests ───────────────────────────────────────────────────────


class TestDiffusersPythonMatrix:
    """Tests for diffusers entries in the Python compatibility matrix."""

    def test_diffusers_in_python_matrix(self):
        """diffusers must exist as a key in PYTHON_MATRIX."""
        assert "diffusers" in PYTHON_MATRIX

    def test_diffusers_has_entries(self):
        """At least one version entry must be defined."""
        entries = get_framework_versions("diffusers")
        assert len(entries) >= 1

    def test_diffusers_0272_exists(self):
        """Specific version 0.27.2 (used in the stable-diffusion profile) must exist."""
        entry = get_framework_entry("diffusers", "0.27.2")
        assert entry is not None
        assert entry.framework == "diffusers"
        assert entry.version == "0.27.2"

    def test_diffusers_0272_python_range(self):
        """diffusers 0.27.2 should support Python 3.8–3.12."""
        entry = get_framework_entry("diffusers", "0.27.2")
        assert entry is not None
        assert entry.min_python == "3.8"
        assert entry.max_python == "3.12"
        assert "3.10" in entry.supported_python
        assert "3.11" in entry.supported_python
        assert "3.12" in entry.supported_python

    def test_diffusers_0272_cuda_support(self):
        """diffusers 0.27.2 should support CUDA 11.8 and 12.1."""
        entry = get_framework_entry("diffusers", "0.27.2")
        assert entry is not None
        assert "11.8" in entry.supported_cuda
        assert "12.1" in entry.supported_cuda

    def test_diffusers_0210_python_range(self):
        """diffusers 0.21.0 should support Python 3.8–3.11 only."""
        entry = get_framework_entry("diffusers", "0.21.0")
        assert entry is not None
        assert "3.12" not in entry.supported_python
        assert "3.8" in entry.supported_python
        assert "3.11" in entry.supported_python

    def test_latest_compatible_diffusers_py311_cuda118(self):
        """Latest diffusers compatible with Python 3.11 + CUDA 11.8 should be 0.27.2."""
        latest = get_latest_compatible_version(
            "diffusers", python_version="3.11", cuda_version="11.8"
        )
        assert latest == "0.27.2"

    def test_latest_compatible_diffusers_py312(self):
        """Latest diffusers compatible with Python 3.12 should be 0.27.2."""
        latest = get_latest_compatible_version("diffusers", python_version="3.12")
        assert latest == "0.27.2"


# ── CUDA Framework Support Tests ──────────────────────────────────────────────


class TestDiffusersCUDASupport:
    """Tests for diffusers entries in FRAMEWORK_CUDA_SUPPORT."""

    def test_diffusers_cuda_support_exists(self):
        """diffusers must have an entry in the CUDA framework support map."""
        cuda_versions = get_supported_cuda_for_framework("diffusers", "0.27.2")
        assert len(cuda_versions) > 0

    def test_diffusers_0272_supports_cuda118(self):
        """diffusers 0.27.2 should support CUDA 11.8."""
        cuda_versions = get_supported_cuda_for_framework("diffusers", "0.27.2")
        assert "11.8" in cuda_versions

    def test_diffusers_0272_supports_cuda121(self):
        """diffusers 0.27.2 should support CUDA 12.1."""
        cuda_versions = get_supported_cuda_for_framework("diffusers", "0.27.2")
        assert "12.1" in cuda_versions

    def test_diffusers_0210_supports_cuda117(self):
        """diffusers 0.21.0 should still support CUDA 11.7."""
        cuda_versions = get_supported_cuda_for_framework("diffusers", "0.21.0")
        assert "11.7" in cuda_versions

    def test_diffusers_unknown_version_empty(self):
        """Unknown diffusers version should return empty list."""
        cuda_versions = get_supported_cuda_for_framework("diffusers", "0.0.0")
        assert cuda_versions == []


# ── Resolver Integration Tests ────────────────────────────────────────────────


class TestDiffusersResolver:
    """Tests for resolving the stable-diffusion profile via CompatibilityResolver."""

    async def test_resolve_diffusers_cuda118_py311(self):
        """Resolve diffusers 0.27.2 with CUDA 11.8 + Python 3.11."""
        result = await R.resolve(
            packages=[
                PackageConstraint("torch", "2.5.0", cuda_variant="cu118"),
                PackageConstraint("diffusers", "0.27.2"),
                PackageConstraint("transformers", "4.40.0"),
                PackageConstraint("accelerate", "0.29.3"),
                PackageConstraint("safetensors", "0.4.3"),
                PackageConstraint("Pillow", "10.3.0"),
                PackageConstraint("numpy", "1.26.4"),
            ],
            python_version="3.11",
            cuda_version="11.8",
            target_os="LINUX",
            profile_slug="stable-diffusion",
            os_support=["LINUX", "WSL"],
            cuda_required=True,
        )
        pkg_names = [p.name for p in result.packages]
        assert "diffusers" in pkg_names
        assert "torch" in pkg_names
        assert "transformers" in pkg_names

        # torch should get the CUDA variant
        torch_pkg = next(p for p in result.packages if p.name == "torch")
        assert torch_pkg.cuda_variant == "cu118"

        # diffusers should NOT have a CUDA variant (it's a pure Python package)
        diff_pkg = next(p for p in result.packages if p.name == "diffusers")
        assert diff_pkg.cuda_variant is None
        assert diff_pkg.version == "0.27.2"

    async def test_resolve_diffusers_cuda121_py312(self):
        """Resolve diffusers with CUDA 12.1 + Python 3.12."""
        result = await R.resolve(
            packages=[
                PackageConstraint("torch", "2.5.0", cuda_variant="cu121"),
                PackageConstraint("diffusers", "0.27.2"),
            ],
            python_version="3.12",
            cuda_version="12.1",
            target_os="LINUX",
            profile_slug="stable-diffusion",
            os_support=["LINUX", "WSL"],
            cuda_required=True,
        )
        assert result.python_version == "3.12"
        assert result.cuda_version == "12.1"

    async def test_resolve_diffusers_unsupported_os_raises(self):
        """stable-diffusion profile does not support Windows natively."""
        with pytest.raises(Exception):  # UnsupportedOSError
            await R.resolve(
                packages=[PackageConstraint("diffusers", "0.27.2")],
                python_version="3.11",
                cuda_version="11.8",
                target_os="WIN",
                profile_slug="stable-diffusion",
                os_support=["LINUX", "WSL"],
                cuda_required=True,
            )

    async def test_resolve_diffusers_no_cuda_raises(self):
        """stable-diffusion profile requires CUDA — omitting it should fail."""
        with pytest.raises(IncompatibilityError) as exc:
            await R.resolve(
                packages=[PackageConstraint("diffusers", "0.27.2")],
                python_version="3.11",
                cuda_version=None,
                target_os="LINUX",
                profile_slug="stable-diffusion",
                os_support=["LINUX", "WSL"],
                cuda_required=True,
            )
        assert exc.value.component == "cuda"

    async def test_resolve_diffusers_python_mismatch_raises(self):
        """diffusers 0.21.0 doesn't support Python 3.12 — should fail."""
        with pytest.raises(IncompatibilityError) as exc:
            await R.resolve(
                packages=[PackageConstraint("diffusers", "0.21.0")],
                python_version="3.12",
                cuda_version="11.8",
                target_os="LINUX",
                profile_slug="stable-diffusion",
                os_support=["LINUX", "WSL"],
                cuda_required=True,
            )
        assert exc.value.component == "python"
