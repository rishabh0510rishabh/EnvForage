"""
GPU detection module.

Detects NVIDIA GPUs via nvidia-smi, AMD GPUs via rocm-smi, and Apple MPS via system detection.
Handles: Linux, Windows, WSL2 (driver is on Windows host), macOS Apple Silicon.
Never raises — returns empty list if detection methods are not available.
"""
from __future__ import annotations

import subprocess

import logging
import platform
import re
import subprocess
from typing import NamedTuple
from envforge_agent.schemas import GPUInfo

logger = logging.getLogger(__name__)


def detect_gpus(timeout: int = 30) -> list[GPUInfo]:
    """
    Detect all GPUs (NVIDIA, AMD, or Apple MPS).
    
    Returns a list of detected GPUs. For Apple Silicon systems with MPS support,
    returns a single GPUInfo with name="Apple Metal Performance Shaders (MPS)".
    """
    # On macOS with Apple Silicon, check for MPS first
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        mps_gpus = _detect_mps()
        if mps_gpus:
            return mps_gpus
    
    # Try NVIDIA detection
    try:
        gpus = _detect_via_nvidia_smi(timeout=timeout)
        if gpus:
            return gpus
    except Exception:
        pass

    # Try AMD ROCm detection
    try:
        return _detect_via_rocm_smi(timeout=timeout)
    except Exception:
        return []


def _detect_via_nvidia_smi(timeout: int = 30) -> list[GPUInfo]:
    """
    Run nvidia-smi with CSV query and parse output.

    Queries: name, memory.total (MiB), driver_version, per GPU index.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        logger.debug("nvidia-smi command not found in system path.")
        return []
    except subprocess.TimeoutExpired:
        logger.debug("nvidia-smi command timed out after 15 seconds.")
        return []
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug("Unexpected error running nvidia-smi: %s", e, exc_info=True)
        return []

    if result.returncode != 0:
        logger.debug(
             "nvidia-smi failed with return code %s. Error: %s",
             result.returncode,
             result.stderr.strip(),
         )
        return []

    gpus: list[GPUInfo] = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue

        index_str, name, memory_mib_str, driver = parts[:4]

        try:
            index = int(index_str)
        except ValueError:
            index = len(gpus)

        vram_gb: float | None = None
        try:
            vram_mib = float(memory_mib_str)
            vram_gb = round(vram_mib / 1024, 2)
        except (ValueError, TypeError):
            pass

        gpus.append(
            GPUInfo(
                name=name,
                vram_gb=vram_gb,
                driver_version=driver if driver and driver != "[N/A]" else None,
                index=index,
            )
        )

    return gpus


def _detect_via_rocm_smi(timeout: int = 30) -> list[GPUInfo]:
    """
    Run rocm-smi and parse JSON output.
    """
    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname", "--showvram", "--showdriverversion", "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return []

    if result.returncode != 0:
        return []

    import json
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    gpus: list[GPUInfo] = []
    # rocm-smi JSON format varies, but usually it's a dict where keys are card0, card1...
    for card_key, info in data.items():
        if not card_key.startswith("card"):
            continue
            
        name = info.get("Product Name", "AMD GPU")
        vram_raw = info.get("VRAM Total Memory (B)", "0")
        driver = info.get("Driver Version")
        
        try:
            vram_gb = round(float(vram_raw) / (1024**3), 2) if vram_raw else None
        except (ValueError, TypeError):
            vram_gb = None
            
        try:
            index = int(card_key.replace("card", ""))
        except ValueError:
            index = len(gpus)

        gpus.append(
            GPUInfo(
                name=name,
                vram_gb=vram_gb,
                driver_version=driver,
                index=index,
            )
        )

    return gpus


def _detect_mps() -> list[GPUInfo]:
    """
    Detect Apple Metal Performance Shaders (MPS) capability on Apple Silicon.
    
    PRECONDITION: Caller has verified this is Darwin + arm64.
    
    MPS requires:
    - Apple Silicon (M1/M2/M3/M4 or variants)
    - macOS 12.3 or later
    - PyTorch or TensorFlow with Metal support (optional check)
    
    This function attempts actual capability detection:
    1. Check macOS version (must be 12.3+)
    2. If PyTorch is available, verify torch.backends.mps.is_available()
    3. If neither check succeeds or passes, report MPS as available but with caveats
    
    Returns: [GPUInfo] if MPS is likely available, [] otherwise
    """
    # Step 1: Check macOS version
    macos_version = _get_macos_version()
    if macos_version is None:
        logger.debug("Could not determine macOS version for MPS capability check")
        return []
    
    major, minor = _parse_macos_version(macos_version)
    
    # MPS requires macOS 12.3 or later
    if (major, minor) < (12, 3):
        logger.debug(
            f"MPS not available: macOS {macos_version} is older than 12.3 (minimum required)"
        )
        return []
    
    # Step 2: Try to verify via PyTorch if available
    pytorch_mps_available = _check_pytorch_mps_available()
    if pytorch_mps_available is not None:
        if pytorch_mps_available:
            logger.debug("PyTorch confirms MPS is available")
            return [
                GPUInfo(
                    name="Apple Metal Performance Shaders (MPS)",
                    vram_gb=None,
                    driver_version=None,
                    index=0,
                )
            ]
        else:
            logger.debug("PyTorch available but MPS is not enabled or unavailable")
            return []
    
    # Step 3: No PyTorch, but macOS version is compatible
    # Report MPS as available with confidence based on version
    logger.debug(f"MPS likely available on macOS {macos_version} (version check passed)")
    return [
        GPUInfo(
            name="Apple Metal Performance Shaders (MPS)",
            vram_gb=None,
            driver_version=None,
            index=0,
        )
    ]


def _get_macos_version() -> str | None:
    """
    Get macOS version string (e.g., "13.5.1").
    
    Returns: Version string, or None if detection fails
    """
    try:
        result = subprocess.run(
            ["sw_vers", "-productVersion"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.debug(f"sw_vers command failed: {e}")

    # Fallback: platform.mac_ver()[0] returns the macOS product version.
    try:
        version = platform.mac_ver()[0]
        return version or None
    except Exception:
        return None


def _parse_macos_version(version_str: str) -> tuple[int, int]:
    """
    Parse macOS version string to (major, minor) tuple.
    
    Examples:
        "13.5.1" -> (13, 5)
        "22.6.0" -> (22, 6)  [Darwin kernel version]
        "12" -> (12, 0)
    
    Returns: (major, minor) tuple, or (0, 0) if parsing fails
    """
    try:
        parts = version_str.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        return (major, minor)
    except (ValueError, IndexError):
        return (0, 0)


def _check_pytorch_mps_available() -> bool | None:
    """
    Check if PyTorch is installed and MPS backend is available.
    
    Returns:
        True if torch.backends.mps.is_available() returns True
        False if torch is available but MPS is not available
        None if PyTorch is not installed (can't verify)
    """
    try:
        import torch
        
        # PyTorch has mps backend
        if hasattr(torch.backends, "mps"):
            result = torch.backends.mps.is_available()
            logger.debug(f"PyTorch MPS availability check: {result}")
            return result
        else:
            logger.debug("PyTorch installed but torch.backends.mps not found")
            return False
    except ImportError:
        logger.debug("PyTorch not installed; cannot verify MPS capability")
        return None
    except Exception as e:
        logger.debug(f"Error checking PyTorch MPS availability: {e}")
        return None
