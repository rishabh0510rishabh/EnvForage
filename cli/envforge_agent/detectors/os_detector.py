"""
OS detection module.

Detects: OS name, version, architecture, and WSL version.
Handles: Linux, Windows, WSL2.
"""

from __future__ import annotations

import platform

from envforge_agent.schemas import OSInfo


def detect_os() -> OSInfo:
    """
    Detect operating system information.

    Returns OSInfo with name, version, architecture, and wsl_version.
    Never raises — falls back to platform.system() on any failure.
    """
    system = platform.system()
    arch = platform.machine()

    if system == "Windows":
        return _detect_windows(arch)
    elif system == "Linux":
        return _detect_linux(arch)
    else:
        return OSInfo(name=system, version=platform.version(), architecture=arch)


# ── Windows ───────────────────────────────────────────────────────────────────


def _detect_windows(arch: str) -> OSInfo:
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        )
        product_name = winreg.QueryValueEx(key, "ProductName")[0]
        build_number = winreg.QueryValueEx(key, "CurrentBuildNumber")[0]
        display_version = winreg.QueryValueEx(key, "DisplayVersion")[0]
        version = f"{display_version} (Build {build_number})"

        name = product_name
        # On Windows 11, ProductName registry key might still report "Windows 10 ..."
        # for backwards compatibility. We correct this by checking build number or platform.release().
        if "Windows 10" in name:
            is_win11 = False
            try:
                if int(build_number) >= 22000:
                    is_win11 = True
            except ValueError:
                pass
            if is_win11 or platform.release() == "11":
                name = name.replace("Windows 10", "Windows 11")
    except Exception:
        name = f"Windows {platform.release()}"
        version = platform.version()

    return OSInfo(name=name, version=version, architecture=arch, wsl_version=None)


# ── Linux / WSL ───────────────────────────────────────────────────────────────


def _detect_linux(arch: str) -> OSInfo:
    name, version = _read_os_release()
    wsl_version = _detect_wsl()
    return OSInfo(name=name, version=version, architecture=arch, wsl_version=wsl_version)


def _read_os_release() -> tuple[str, str]:
    """Read /etc/os-release for distro name and version."""
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            lines = f.readlines()
        data: dict[str, str] = {}
        for line in lines:
            line = line.strip()
            if "=" in line:
                key, _, val = line.partition("=")
                data[key] = val.strip('"')
        name = data.get("PRETTY_NAME") or data.get("NAME") or "Linux"
        version = data.get("VERSION_ID") or data.get("VERSION") or platform.release()
        return name, version
    except FileNotFoundError:
        # Fallback: use platform module
        return f"Linux {platform.release()}", platform.release()
    except Exception:
        return "Linux", platform.release()


def _detect_wsl() -> str | None:
    """
    Detect if running under WSL and return the version string.

    Detection methods (in order):
    1. Check /proc/version for "Microsoft" or "WSL"
    2. Check WSL_DISTRO_NAME environment variable
    3. Check /proc/sys/kernel/osrelease for "microsoft"
    """
    import os

    # Method 1: Environment variable (most reliable in WSL2)
    if os.environ.get("WSL_DISTRO_NAME"):
        return "WSL2"

    # Method 2: /proc/version content check
    try:
        with open("/proc/version", encoding="utf-8") as f:
            proc_version = f.read().lower()
        if "microsoft" in proc_version or "wsl" in proc_version:
            # Distinguish WSL1 vs WSL2 via /proc/sys/kernel/osrelease
            try:
                with open("/proc/sys/kernel/osrelease", encoding="utf-8") as f:
                    kernel = f.read().lower()
                if "microsoft-standard" in kernel:
                    return "WSL2"
                elif "microsoft" in kernel:
                    return "WSL1"
            except Exception:
                return "WSL2"  # Assume WSL2 if /proc/version says Microsoft
    except Exception:
        pass

    return None
