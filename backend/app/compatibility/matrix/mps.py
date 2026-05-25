"""
Apple Metal Performance Shaders (MPS) compatibility matrix.

MPS is available on all Apple Silicon Macs (M1/M2/M3/M4 and variants) running
macOS 12.3 or later. This module defines compatible framework versions for MPS.

Sources:
  - PyTorch MPS: https://pytorch.org/docs/stable/notes/mps.html
  - TensorFlow Metal: https://github.com/apple/tensorflow_metal
"""
from __future__ import annotations

from app.compatibility.errors import UnknownVersionError

# ── PyTorch + MPS ─────────────────────────────────────────────────────────

# PyTorch version -> minimum macOS version required for MPS
PYTORCH_MPS_REQUIREMENTS = {
    "2.0.0": "12.3",
    "2.0.1": "12.3",
    "2.1.0": "12.3",
    "2.1.1": "12.3",
    "2.1.2": "12.3",
    "2.2.0": "12.3",
    "2.2.1": "12.3",
    "2.3.0": "12.3",
    "2.3.1": "12.3",
    "2.4.0": "12.3",
    "2.5.0": "12.3",
}

# TensorFlow + Metal compatibility
# tensorflow-metal is only available for TensorFlow 2.11+
TENSORFLOW_METAL_REQUIREMENTS = {
    "2.11.0": "12.1",
    "2.11.1": "12.1",
    "2.12.0": "12.1",
    "2.12.1": "12.1",
    "2.13.0": "12.1",
    "2.13.1": "12.1",
    "2.14.0": "12.1",
    "2.14.1": "12.1",
    "2.15.0": "12.1",
    "2.15.1": "12.1",
    "2.16.0": "12.1",
}


def get_pytorch_mps_min_version(pytorch_version: str) -> str | None:
    """
    Get the minimum macOS version required for a given PyTorch version with MPS.
    
    Args:
        pytorch_version: PyTorch version string (e.g. "2.1.0")
    
    Returns:
        Minimum macOS version as string (e.g. "12.3"), or None if version not supported
    """
    return PYTORCH_MPS_REQUIREMENTS.get(pytorch_version)


def get_tensorflow_metal_min_version(tensorflow_version: str) -> str | None:
    """
    Get the minimum macOS version required for TensorFlow Metal support.
    
    Args:
        tensorflow_version: TensorFlow version string (e.g. "2.13.0")
    
    Returns:
        Minimum macOS version as string (e.g. "12.1"), or None if version not supported
    """
    return TENSORFLOW_METAL_REQUIREMENTS.get(tensorflow_version)


def validate_pytorch_mps_support(
    pytorch_version: str,
    macos_version: str,
) -> tuple[bool, str]:
    """
    Validate if PyTorch with MPS is supported on the given macOS version.
    
    Args:
        pytorch_version: PyTorch version (e.g. "2.1.0")
        macos_version: macOS version (e.g. "13.0")
    
    Returns:
        (is_supported, reason) tuple
    """
    min_version = get_pytorch_mps_min_version(pytorch_version)
    
    if min_version is None:
        return False, f"PyTorch {pytorch_version} is not in the MPS compatibility matrix"
    
    # Simple version comparison (major.minor)
    user_major, user_minor = _parse_version(macos_version)
    min_major, min_minor = _parse_version(min_version)
    
    if (user_major, user_minor) >= (min_major, min_minor):
        return True, f"PyTorch {pytorch_version} with MPS is supported on macOS {macos_version}"
    else:
        return False, (
            f"PyTorch {pytorch_version} with MPS requires macOS {min_version} or later. "
            f"You have macOS {macos_version}."
        )


def validate_tensorflow_metal_support(
    tensorflow_version: str,
    macos_version: str,
) -> tuple[bool, str]:
    """
    Validate if TensorFlow Metal is supported on the given macOS version.
    
    Args:
        tensorflow_version: TensorFlow version (e.g. "2.13.0")
        macos_version: macOS version (e.g. "13.0")
    
    Returns:
        (is_supported, reason) tuple
    """
    min_version = get_tensorflow_metal_min_version(tensorflow_version)
    
    if min_version is None:
        return False, (
            f"TensorFlow {tensorflow_version} is not supported with Metal. "
            f"TensorFlow 2.11+ supports tensorflow-metal."
        )
    
    # Simple version comparison
    user_major, user_minor = _parse_version(macos_version)
    min_major, min_minor = _parse_version(min_version)
    
    if (user_major, user_minor) >= (min_major, min_minor):
        return True, f"TensorFlow {tensorflow_version} with Metal is supported on macOS {macos_version}"
    else:
        return False, (
            f"TensorFlow {tensorflow_version} with Metal requires macOS {min_version} or later. "
            f"You have macOS {macos_version}."
        )


def _parse_version(version_str: str) -> tuple[int, int]:
    """
    Parse version string to (major, minor) tuple.
    
    Examples:
        "12.3" -> (12, 3)
        "13" -> (13, 0)
        "13.0.1" -> (13, 0)
    """
    parts = version_str.split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        return (major, minor)
    except (ValueError, IndexError):
        return (0, 0)
