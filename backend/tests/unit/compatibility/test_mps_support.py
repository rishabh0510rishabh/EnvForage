"""
Unit tests for Apple Silicon / MPS support in the Compatibility Engine.
Tests for: backend/app/compatibility/matrix/mps.py
"""
import pytest

from app.compatibility.errors import (
    IncompatibilityError,
    UnsupportedOSError,
)
from app.compatibility.models import PackageConstraint, OSTarget
from app.compatibility.resolver import CompatibilityResolver
from app.compatibility.matrix.mps import (
    get_pytorch_mps_min_version,
    get_tensorflow_metal_min_version,
    validate_pytorch_mps_support,
    validate_tensorflow_metal_support,
)


class TestPytorchMpsMatrix:
    """Tests for PyTorch + MPS compatibility matrix."""

    def test_pytorch_2_5_mps_available(self):
        """PyTorch 2.5.0 should be in MPS matrix."""
        min_version = get_pytorch_mps_min_version("2.5.0")
        assert min_version == "12.3"

    def test_pytorch_2_1_mps_available(self):
        """PyTorch 2.1.0 should be in MPS matrix."""
        min_version = get_pytorch_mps_min_version("2.1.0")
        assert min_version == "12.3"

    def test_pytorch_unknown_version(self):
        """Unknown PyTorch version returns None."""
        min_version = get_pytorch_mps_min_version("1.13.0")
        assert min_version is None

    def test_pytorch_mps_requires_macos_12_3(self):
        """All PyTorch versions in matrix require macOS 12.3+."""
        versions = ["2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.4.0", "2.5.0"]
        for version in versions:
            min_version = get_pytorch_mps_min_version(version)
            assert min_version == "12.3", f"PyTorch {version} should require 12.3"


class TestTensorflowMetalMatrix:
    """Tests for TensorFlow + Metal compatibility matrix."""

    def test_tensorflow_2_16_metal_available(self):
        """TensorFlow 2.16.0 should be in Metal matrix."""
        min_version = get_tensorflow_metal_min_version("2.16.0")
        assert min_version == "12.1"

    def test_tensorflow_2_13_metal_available(self):
        """TensorFlow 2.13.0 should be in Metal matrix."""
        min_version = get_tensorflow_metal_min_version("2.13.0")
        assert min_version == "12.1"

    def test_tensorflow_2_10_not_supported(self):
        """TensorFlow 2.10 (pre-Metal) returns None."""
        min_version = get_tensorflow_metal_min_version("2.10.0")
        assert min_version is None

    def test_tensorflow_metal_requires_macos_12_1(self):
        """All TensorFlow versions in matrix require macOS 12.1+."""
        versions = ["2.11.0", "2.12.0", "2.13.0", "2.14.0", "2.15.0", "2.16.0"]
        for version in versions:
            min_version = get_tensorflow_metal_min_version(version)
            assert min_version == "12.1", f"TensorFlow {version} should require 12.1"


class TestValidatePytorchMps:
    """Tests for validate_pytorch_mps_support()."""

    def test_pytorch_mps_macos_13_5_supported(self):
        """PyTorch 2.5.0 on macOS 13.5 should be supported."""
        supported, reason = validate_pytorch_mps_support("2.5.0", "13.5.1")
        assert supported is True
        assert "supported" in reason.lower()

    def test_pytorch_mps_macos_12_3_minimum(self):
        """PyTorch 2.1.0 on macOS 12.3 (minimum) should be supported."""
        supported, reason = validate_pytorch_mps_support("2.1.0", "12.3")
        assert supported is True

    def test_pytorch_mps_macos_12_2_unsupported(self):
        """PyTorch 2.1.0 on macOS 12.2 (below minimum) should fail."""
        supported, reason = validate_pytorch_mps_support("2.1.0", "12.2")
        assert supported is False
        assert "12.3" in reason

    def test_pytorch_unknown_version_unsupported(self):
        """Unknown PyTorch version should return False."""
        supported, reason = validate_pytorch_mps_support("1.13.0", "13.0")
        assert supported is False
        assert "not in" in reason.lower()


class TestValidateTensorflowMetal:
    """Tests for validate_tensorflow_metal_support()."""

    def test_tensorflow_metal_macos_12_1_supported(self):
        """TensorFlow 2.16.0 on macOS 12.1 (minimum) should be supported."""
        supported, reason = validate_tensorflow_metal_support("2.16.0", "12.1")
        assert supported is True

    def test_tensorflow_metal_macos_13_0_supported(self):
        """TensorFlow 2.13.0 on macOS 13.0 should be supported."""
        supported, reason = validate_tensorflow_metal_support("2.13.0", "13.0")
        assert supported is True

    def test_tensorflow_metal_macos_12_0_unsupported(self):
        """TensorFlow 2.13.0 on macOS 12.0 (below minimum) should fail."""
        supported, reason = validate_tensorflow_metal_support("2.13.0", "12.0")
        assert supported is False
        assert "12.1" in reason

    def test_tensorflow_2_10_not_supported(self):
        """TensorFlow 2.10.0 (pre-Metal) on macOS 13.0 should fail."""
        supported, reason = validate_tensorflow_metal_support("2.10.0", "13.0")
        assert supported is False
        assert "2.11" in reason


class TestResolverMacosSupport:
    """Tests for Compatibility Resolver with macOS target."""

    def test_resolve_pytorch_mps_macos(self):
        """Resolver should accept macOS as target_os."""
        resolver = CompatibilityResolver()
        result = resolver.resolve(
            packages=[PackageConstraint("torch", "2.5.0")],
            python_version="3.11",
            cuda_version=None,
            target_os="MACOS",
            profile_slug="pytorch-mps",
            os_support=["MACOS"],
            cuda_required=False,
        )
        assert result.target_os == "MACOS"
        assert result.cuda_version is None
        assert len(result.packages) > 0

    def test_resolve_tensorflow_metal_macos(self):
        """Resolver should resolve TensorFlow + Metal for macOS."""
        resolver = CompatibilityResolver()
        result = resolver.resolve(
            packages=[
                PackageConstraint("tensorflow", "2.16.0"),
                PackageConstraint("tensorflow-metal", "1.1.0"),
            ],
            python_version="3.11",
            cuda_version=None,
            target_os="MACOS",
            profile_slug="tensorflow-metal",
            os_support=["MACOS"],
            cuda_required=False,
        )
        assert result.target_os == "MACOS"
        assert len(result.packages) == 2

    def test_resolve_pytorch_mps_unsupported_os(self):
        """Resolver should reject pytorch-mps on unsupported OS."""
        resolver = CompatibilityResolver()
        
        # pytorch-mps only supports MACOS, not LINUX
        with pytest.raises(UnsupportedOSError) as exc:
            resolver.resolve(
                packages=[PackageConstraint("torch", "2.5.0")],
                python_version="3.11",
                cuda_version=None,
                target_os="LINUX",
                profile_slug="pytorch-mps",
                os_support=["MACOS"],
                cuda_required=False,
            )
        assert exc.value.requested_os == "LINUX"

    def test_macos_warnings_include_mps_note(self):
        """Resolver should include MPS note in warnings for PyTorch on macOS."""
        resolver = CompatibilityResolver()
        result = resolver.resolve(
            packages=[PackageConstraint("torch", "2.5.0")],
            python_version="3.11",
            cuda_version=None,
            target_os="MACOS",
            profile_slug="pytorch-mps",
            os_support=["MACOS"],
            cuda_required=False,
        )
        # Should have warnings mentioning MPS or Metal
        assert len(result.warnings) > 0
        warning_text = " ".join(result.warnings).lower()
        assert "mps" in warning_text or "metal" in warning_text

    def test_macos_warnings_include_tensorflow_metal_note(self):
        """Resolver should include Metal note in warnings for TensorFlow on macOS."""
        resolver = CompatibilityResolver()
        result = resolver.resolve(
            packages=[
                PackageConstraint("tensorflow", "2.16.0"),
                PackageConstraint("tensorflow-metal", "1.1.0"),
            ],
            python_version="3.11",
            cuda_version=None,
            target_os="MACOS",
            profile_slug="tensorflow-metal",
            os_support=["MACOS"],
            cuda_required=False,
        )
        # Should have warnings mentioning Metal
        assert len(result.warnings) > 0
        warning_text = " ".join(result.warnings).lower()
        assert "metal" in warning_text


class TestOsTargetMacos:
    """Tests for OSTarget model with MACOS support."""

    def test_os_target_includes_macos(self):
        """OSTarget type should include MACOS."""
        from app.compatibility.models import OSTarget
        from typing import get_args
        
        valid_targets = get_args(OSTarget)
        assert "MACOS" in valid_targets
        assert "LINUX" in valid_targets
        assert "WSL" in valid_targets
        assert "WIN" in valid_targets

    def test_resolved_environment_macos_target(self):
        """ResolvedEnvironment should accept MACOS target_os."""
        from app.compatibility.models import ResolvedEnvironment, ResolvedPackage
        
        env = ResolvedEnvironment(
            python_version="3.11",
            cuda_version=None,
            target_os="MACOS",
            rocm_version=None,
            packages=[
                ResolvedPackage(name="torch", version="2.5.0", cuda_variant=None),
            ],
            warnings=["MPS available"],
        )
        assert env.target_os == "MACOS"
        assert env.cuda_version is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
