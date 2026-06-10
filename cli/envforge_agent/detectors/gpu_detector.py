"""
GPU detection module.

Detects NVIDIA GPUs via nvidia-smi.
Handles: Linux, Windows, WSL2 (driver is on Windows host).
Never raises — returns empty list if nvidia-smi is not available.
"""

from __future__ import annotations

import os
import stat
import subprocess

import logging
from envforge_agent.detectors.os_detector import _detect_wsl
from envforge_agent.schemas import GPUInfo

logger = logging.getLogger(__name__)


def detect_gpus(timeout: int = 30) -> list[GPUInfo]:
    """
    Detect all GPUs (NVIDIA or AMD).
    """
    try:
        gpus = _detect_via_nvidia_smi(timeout=timeout)
        if gpus:
            return gpus
    except Exception:
        pass

    try:
        return _detect_via_rocm_smi(timeout=timeout)
    except Exception:
        return []


def detect_wsl_gpu_passthrough(timeout: int = 30) -> tuple[bool, list[str]]:
    """
    Diagnose WSL2 GPU passthrough health.

    Returns a tuple of (available, issues). When running under WSL2,
    this checks /dev/dxg, nvidia-smi availability, and NVIDIA container
    toolkit readiness.
    """
    issues: list[str] = []
    if _detect_wsl() != "WSL2":
        return True, issues

    if not _check_dxg_present():
        issues.append("Missing /dev/dxg — WSL GPU passthrough is unavailable.")

    if not _check_nvidia_smi(timeout=timeout):
        issues.append("`nvidia-smi` failed inside WSL2. Verify NVIDIA drivers and WSL integration.")

    if not _check_nvidia_container_toolkit():
        issues.append(
            "NVIDIA container toolkit not available in WSL2. Docker GPU runtime may be broken."
        )

    return len(issues) == 0, issues


def _check_dxg_present() -> bool:
    if not os.path.exists("/dev/dxg"):
        return False

    try:
        mode = os.stat("/dev/dxg").st_mode
        return stat.S_ISCHR(mode) or stat.S_ISBLK(mode)
    except OSError:
        return False


def _check_nvidia_smi(timeout: int = 30) -> bool:
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return False

    return result.returncode == 0 and bool(result.stdout.strip())


def _check_nvidia_container_toolkit() -> bool:
    try:
        result = subprocess.run(
            ["nvidia-container-cli", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return False

    return result.returncode == 0


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
            timeout=15,
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
        logger.debug("rocm-smi command not found in system path.")
        return []
    except subprocess.TimeoutExpired:
        logger.debug("rocm-smi command timed out after %s seconds.", timeout)
        return []
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug("Unexpected error running rocm-smi: %s", e, exc_info=True)
        return []

    if result.returncode != 0:
        return []

    import json
    
    out_str = result.stdout
    start_idx = out_str.find('{')
    end_idx = out_str.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = out_str[start_idx:end_idx+1]
    else:
        json_str = out_str

    try:
        data = json.loads(json_str)
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
