"""
Python environment detection module.

Scans for all Python installations reachable from PATH and common
install locations. For each, records version, path, pip version,
and whether it's a virtual environment.

Strategy:
  1. Try python3.9 through python3.13 binaries in PATH
  2. Try `python3` and `python` as fallbacks
  3. On Windows, also try `py -X.Y` (Python Launcher)
  4. Detect active_python from sys.executable
  5. Determine is_venv from sys.prefix vs sys.base_prefix
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

from envforge_agent.schemas import PythonInfo

# Python versions to probe (3.8–3.13)
_PROBE_VERSIONS = ["3.8", "3.9", "3.10", "3.11", "3.12","3.13"]

# Inspector script run inside each discovered Python to get its full info
_INSPECTOR = """
import sys, json, os
prefix = getattr(sys, 'prefix', sys.executable)
base = getattr(sys, 'base_prefix', prefix)
is_venv = prefix != base
venv_path = prefix if is_venv else None
try:
    import pip
    pip_ver = pip.__version__
except ImportError:
    pip_ver = None
print(json.dumps({
    "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    "path": sys.executable,
    "is_venv": is_venv,
    "venv_path": venv_path,
    "pip_version": pip_ver,
}))
"""


def detect_python() -> tuple[list[PythonInfo], PythonInfo | None]:
    """
    Detect all Python installations and identify the active one.

    Returns:
        (installations, active_python)
        - installations: all unique Python executables found
        - active_python: the Python running this agent
    """
    candidates = _collect_candidate_binaries()
    seen_paths: set[str] = set()
    installations: list[PythonInfo] = []

    for binary in candidates:
        info = _inspect_python(binary)
        if info is None:
            continue
        real_path = str(Path(info.path).resolve())
        if real_path in seen_paths:
            continue
        seen_paths.add(real_path)
        installations.append(info)

    # Sort by version descending
    installations.sort(
        key=lambda p: tuple(int(x) for x in p.version.split(".")[:3]),
        reverse=True,
    )

    active_python = _detect_active_python()
    return installations, active_python


def _collect_candidate_binaries() -> list[str]:
    """Build the list of python binaries to probe."""
    candidates: list[str] = []

    if platform.system() == "Windows":
        # Windows Python Launcher: py -3.11 etc.
        for ver in _PROBE_VERSIONS:
            candidates.append(f"py -{ver}")
        candidates += ["python", "python3"]
    else:
        # Linux / WSL: probe versioned binaries first
        for ver in _PROBE_VERSIONS:
            candidates.append(f"python{ver}")
        candidates += ["python3", "python"]

    # Also include the agent's own interpreter (always valid)
    candidates.insert(0, sys.executable)

    return candidates


def _inspect_python(binary: str) -> PythonInfo | None:
    """
    Run the inspector script inside the given Python binary.
    Returns None if the binary is not found or fails.
    """
    try:
        # Handle "py -3.11" style on Windows
        if binary.startswith("py -"):
            args = ["py", binary[3:].strip(), "-c", _INSPECTOR]
        else:
            args = [binary, "-c", _INSPECTOR]

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None

        data = json.loads(result.stdout.strip())
        return PythonInfo(
            version=data["version"],
            path=data["path"],
            is_venv=data["is_venv"],
            venv_path=data.get("venv_path"),
            pip_version=data.get("pip_version"),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired,
            json.JSONDecodeError, KeyError, ValueError):
        return None


def _detect_active_python() -> PythonInfo | None:
    """Return info for the Python interpreter currently running this agent."""
    return _inspect_python(sys.executable)
