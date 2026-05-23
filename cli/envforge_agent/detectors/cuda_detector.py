"""
CUDA detection module.

Detects: CUDA toolkit version, toolkit path, cuDNN version, NCCL version.

Detection strategy (in order of reliability):
  1. nvcc --version              → CUDA toolkit version
  2. /usr/local/cuda/version.txt  → Linux standard path
  3. CUDA_PATH / CUDA_HOME env vars → Windows / user-set
  4. nvidia-smi for driver-reported CUDA version (fallback)

cuDNN detection:
  1. Find cudnn.h or cudnn_version.h and parse #define macros
  2. Python: import torch; torch.backends.cudnn.version()
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from envforge_agent.schemas import CUDAInfo


def detect_cuda() -> CUDAInfo:
    """
    Detect CUDA installation details.
    Returns CUDAInfo with all None fields if CUDA is not installed.
    Never raises.
    """
    version = _detect_cuda_version()
    toolkit_path = _detect_toolkit_path(version)
    cudnn_version = _detect_cudnn(toolkit_path)
    nccl_version = _detect_nccl(toolkit_path)

    return CUDAInfo(
        version=version,
        toolkit_path=toolkit_path,
        cudnn_version=cudnn_version,
        nccl_version=nccl_version,
    )


# ── CUDA version ──────────────────────────────────────────────────────────────

def _detect_cuda_version() -> str | None:
    # Method 1: nvcc --version (most reliable — requires CUDA toolkit installed)
    version = _nvcc_version()
    if version:
        return version

    # Method 2: Read version.txt from standard paths
    version = _read_version_txt()
    if version:
        return version

    # Method 3: CUDA_PATH / CUDA_HOME environment variable
    version = _cuda_path_env_version()
    if version:
        return version

    # Method 4: nvidia-smi CUDA version (driver-level, may differ from toolkit)
    version = _nvidia_smi_cuda_version()
    if version:
        return version

    return None


def _nvcc_version() -> str | None:
    """Parse CUDA version from `nvcc --version`."""
    try:
        result = subprocess.run(
            ["nvcc", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        # e.g. "Cuda compilation tools, release 12.1, V12.1.105"
        match = re.search(r"release\s+(\d+\.\d+)", result.stdout)
        return match.group(1) if match else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _read_version_txt() -> str | None:
    """Read CUDA version from /usr/local/cuda/version.txt or version.json."""
    candidate_paths = [
        Path("/usr/local/cuda/version.txt"),
        Path("/usr/local/cuda/version.json"),
    ]
    # Also check /usr/local/cuda-X.Y/version.txt for all installed versions
    try:
        cuda_base = Path("/usr/local")
        for d in cuda_base.iterdir():
            if d.name.startswith("cuda-") and d.is_dir():
                candidate_paths.insert(0, d / "version.txt")
    except (PermissionError, FileNotFoundError):
        pass

    for path in candidate_paths:
        try:
            content = path.read_text(encoding="utf-8")
            # "CUDA Version 12.1.105" or "CUDA Version 12.1"
            match = re.search(r"CUDA\s+Version\s+(\d+\.\d+)", content, re.IGNORECASE)
            if match:
                return match.group(1)
        except (FileNotFoundError, PermissionError):
            continue

    return None


def _cuda_path_env_version() -> str | None:
    """Extract CUDA version from CUDA_PATH or CUDA_HOME env variable path."""
    for env_var in ("CUDA_PATH", "CUDA_HOME", "CUDA_ROOT"):
        path_str = os.environ.get(env_var)
        if path_str:
            # e.g. C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
            # or /usr/local/cuda-12.1
            match = re.search(r"(\d+\.\d+)", path_str)
            if match:
                return match.group(1)
    return None


def _nvidia_smi_cuda_version() -> str | None:
    """Get CUDA version from nvidia-smi (driver-reported, not toolkit)."""
    # Method A: Try specific query-gpu first
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=cuda_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            ver = result.stdout.strip().splitlines()[0].strip()
            if ver and re.match(r"\d+\.\d+", ver):
                return ver
    except (FileNotFoundError, subprocess.TimeoutExpired, IndexError):
        pass

    # Method B: Fall back to standard nvidia-smi output and regex parsing
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            match = re.search(r"CUDA\s+Version:\s*(\d+\.\d+)", result.stdout)
            if match:
                return match.group(1)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


# ── Toolkit path ──────────────────────────────────────────────────────────────

def _detect_toolkit_path(cuda_version: str | None) -> str | None:
    """Find the CUDA toolkit installation directory."""
    # Check explicit env vars first
    for env_var in ("CUDA_PATH", "CUDA_HOME", "CUDA_ROOT"):
        path = os.environ.get(env_var)
        if path and Path(path).exists():
            return path

    # Linux standard paths
    if cuda_version:
        versioned = Path(f"/usr/local/cuda-{cuda_version}")
        if versioned.exists():
            return str(versioned)

    generic = Path("/usr/local/cuda")
    if generic.exists():
        return str(generic)

    # Windows: CUDA default install location
    win_base = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA")
    if win_base.exists():
        try:
            subdirs = sorted(win_base.iterdir(), reverse=True)
            for d in subdirs:
                if d.is_dir() and d.name.startswith("v"):
                    return str(d)
        except (PermissionError, FileNotFoundError):
            pass

    return None


# ── cuDNN ─────────────────────────────────────────────────────────────────────

def _detect_cudnn(toolkit_path: str | None) -> str | None:
    """Detect cuDNN version by parsing header files."""
    search_paths: list[Path] = []

    if toolkit_path:
        base = Path(toolkit_path)
        search_paths += [
            base / "include" / "cudnn_version.h",
            base / "include" / "cudnn.h",
        ]

    # Standard Linux paths
    search_paths += [
        Path("/usr/include/cudnn_version.h"),
        Path("/usr/include/cudnn.h"),
        Path("/usr/local/include/cudnn_version.h"),
    ]

    for header in search_paths:
        version = _parse_cudnn_header(header)
        if version:
            return version

    # Fallback: try PyTorch (if installed in the current Python)
    return _detect_cudnn_via_torch()


def _parse_cudnn_header(header_path: Path) -> str | None:
    """Extract major.minor.patch from a cuDNN header file."""
    try:
        content = header_path.read_text(encoding="utf-8", errors="ignore")
        major = re.search(r"#define\s+CUDNN_MAJOR\s+(\d+)", content)
        minor = re.search(r"#define\s+CUDNN_MINOR\s+(\d+)", content)
        patch = re.search(r"#define\s+CUDNN_PATCHLEVEL\s+(\d+)", content)
        if major and minor and patch:
            return f"{major.group(1)}.{minor.group(1)}.{patch.group(1)}"
    except (FileNotFoundError, PermissionError):
        pass
    return None


def _detect_cudnn_via_torch() -> str | None:
    """Try importing PyTorch to get cuDNN version."""
    try:
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "-c",
             "import torch; print(torch.backends.cudnn.version())"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            raw = result.stdout.strip()
            # cuDNN version is reported as integer e.g. "8902" = 8.9.02
            if raw.isdigit():
                n = int(raw)
                major = n // 1000
                minor = (n % 1000) // 100
                patch = n % 100
                return f"{major}.{minor}.{patch}"
    except Exception:
        pass
    return None


# ── NCCL ──────────────────────────────────────────────────────────────────────

def _detect_nccl(toolkit_path: str | None) -> str | None:
    """Detect NCCL version via header or PyTorch."""
    if toolkit_path:
        nccl_header = Path(toolkit_path) / "include" / "nccl.h"
        try:
            content = nccl_header.read_text(encoding="utf-8", errors="ignore")
            major = re.search(r"#define\s+NCCL_MAJOR\s+(\d+)", content)
            minor = re.search(r"#define\s+NCCL_MINOR\s+(\d+)", content)
            patch = re.search(r"#define\s+NCCL_PATCH\s+(\d+)", content)
            if major and minor and patch:
                return f"{major.group(1)}.{minor.group(1)}.{patch.group(1)}"
        except (FileNotFoundError, PermissionError):
            pass

    # Fallback: PyTorch
    try:
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "-c", "import torch; print(torch.cuda.nccl.version())"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            raw = result.stdout.strip()
            # Returns tuple string e.g. "(2, 18, 1)" or "2.18.1"
            nums = re.findall(r"\d+", raw)
            if len(nums) >= 3:
                return f"{nums[0]}.{nums[1]}.{nums[2]}"
    except Exception:
        pass

    return None
