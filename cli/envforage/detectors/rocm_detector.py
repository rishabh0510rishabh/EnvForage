"""
ROCm software stack detector.

Detects ROCm version and GCN architecture.
Sources:
  - /opt/rocm/.info/version
  - hipcc --version
  - rocminfo
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from envforage.schemas import ROCMInfo


def detect_rocm() -> ROCMInfo:
    """
    Main entry point for ROCm detection.
    Tries multiple methods to find the ROCm version.
    """
    version = _detect_version_file() or _detect_via_hipcc()
    gcn_arch = _detect_gcn_arch()

    return ROCMInfo(
        version=version,
        gcn_arch=gcn_arch,
    )


def _detect_version_file() -> str | None:
    """Read version from /opt/rocm/.info/version (standard location)."""
    vfile = Path("/opt/rocm/.info/version")
    if vfile.exists():
        try:
            return vfile.read_text().strip()
        except Exception:
            pass
    return None


def _detect_via_hipcc() -> str | None:
    """Run hipcc --version and parse the output."""
    try:
        result = subprocess.run(["hipcc", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Output format usually contains: ROCm version: 5.6.0
            match = re.search(r"ROCm version:\s+([\d\.]+)", result.stdout)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


def _detect_gcn_arch() -> str | None:
    """Run rocminfo to find the GCN architecture (e.g., gfx1030)."""
    try:
        result = subprocess.run(["rocminfo"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Look for lines like: Name: gfx1030
            match = re.search(r"Name:\s+(gfx\w+)", result.stdout)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None
