"""
System detection module — CPU and RAM.

Uses psutil for cross-platform support (Linux, Windows, WSL2).
Never raises — falls back to zeroes on any failure.
"""

from __future__ import annotations

import platform
import shutil
import psutil

from envforge_agent.schemas import CPUInfo, RAMInfo, DISKInfo


def detect_cpu() -> CPUInfo:
    """
    Detect CPU information using psutil + platform.

    Returns:
        CPUInfo with brand name, physical core count, and logical thread count.
    """
    brand = _get_cpu_brand()
    cores = psutil.cpu_count(logical=False) or 1
    threads = psutil.cpu_count(logical=True) or cores

    return CPUInfo(brand=brand, cores=cores, threads=threads)


def detect_ram() -> RAMInfo:
    """
    Detect RAM information using psutil.

    Returns:
        RAMInfo with total and available GB (rounded to 2 decimal places).
    """
    try:
        mem = psutil.virtual_memory()
        total_gb = round(mem.total / (1024**3), 2)
        available_gb = round(mem.available / (1024**3), 2)
        return RAMInfo(total_gb=total_gb, available_gb=available_gb)
    except Exception:
        return RAMInfo(total_gb=0.0, available_gb=0.0)


def _get_cpu_brand() -> str:
    """Get CPU brand string across platforms."""
    # Linux: read from /proc/cpuinfo
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except (FileNotFoundError, PermissionError):
            pass

    # Windows: read from winreg
    if platform.system() == "Windows":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except Exception:
            pass

    # Universal fallback: platform.processor() (less specific but always available)
    brand = platform.processor()
    return brand if brand else "Unknown CPU"


def detect_disk() -> DISKInfo:
    """
    Detect available disk space using shutil.

    Returns:
        DISKInfo with total_gb and available_gb (rounded to 2 decimal places).
        Falls back to zeroes on any failure.
    """
    try:
        import os

        if platform.system() == "Windows":
            root_path = os.environ.get("SystemDrive", "C:") + "\\"
        else:
            root_path = "/"

        usage = shutil.disk_usage(root_path)
        total_gb = round(usage.total / (1024**3), 2)
        free_gb = round(usage.free / (1024**3), 2)
        return DISKInfo(total_gb=total_gb, available_gb=free_gb)
    except Exception:
        return DISKInfo(total_gb=0.0, available_gb=0.0)
