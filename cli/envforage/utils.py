from envforage.schemas import DiagnosticReport


def _map_os_to_target(report: DiagnosticReport) -> str:
    """Map detected operating system to EnvForage target identifier."""
    if report.os.wsl_version:
        return "WSL"
    if "windows" in report.os.name.lower():
        return "WIN"
    return "LINUX"


def _extract_python_version(report: DiagnosticReport) -> str:
    """Extract major.minor Python version from DiagnosticReport."""
    if report.active_python:
        version = report.active_python.version
        parts = version.split(".")
        if len(parts) >= 2 and parts[0] and parts[1]:
            return f"{parts[0]}.{parts[1]}"
    return "3.11"  # safe default


def check_for_updates() -> None:
    """Check PyPI for a newer version of envforage.

    Fails completely silently on any network, request, or parsing errors
    to prevent crashing the CLI command execution.
    """
    import sys
    import httpx
    import click
    from envforage import __version__
    from envforage.config import load_config

    # Suppress update checks if quiet output is requested
    if any(
        tok == "--quiet" or (tok.startswith("-") and "q" in tok.lstrip("-")) for tok in sys.argv
    ):
        return

    try:
        from packaging.version import InvalidVersion, Version
    except ImportError:
        # Skip the update check if packaging is not installed
        return

    url = "https://pypi.org/pypi/envforage/json"
    try:
        with httpx.Client(timeout=1.5) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()

            latest_version = data.get("info", {}).get("version")
            if not latest_version:
                return

            try:
                is_newer = Version(latest_version) > Version(__version__)
            except InvalidVersion:
                return

            if is_newer:
                config = load_config()
                if config.auto_update and sys.stdin.isatty():
                    # Prompt Mode
                    prompt_msg = (
                        f"\n[!] A new version of EnvForage is available ({latest_version}).\n"
                        f"    Would you like to update now? [y/N]: "
                    )
                    if click.confirm(prompt_msg, default=False, err=True):
                        run_upgrade(interactive=False)
                        sys.exit(0)
                else:
                    # Notification Mode
                    click.echo(
                        f"\n[!] A new version of envforage is available: {latest_version} (Current: {__version__})\n"
                        f"    Run 'envforage upgrade' to update.\n",
                        err=True,
                    )
    except (httpx.HTTPError, httpx.RequestError, ValueError, KeyError):
        # Gracefully absorb all network/parsing exceptions (JSONDecodeError, ConnectError, HTTPStatusError, etc.)
        pass


def run_upgrade(interactive: bool = True) -> None:
    """Perform the upgrade based on package environment."""
    import sys
    import click
    import subprocess

    is_frozen = getattr(sys, "frozen", False)

    if is_frozen:
        if interactive:
            click.echo("Checking GitHub Releases for the latest standalone installer...")

        repo = "rishabh0510rishabh/EnvForage"
        url = f"https://api.github.com/repos/{repo}/releases/latest"

        import httpx
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

                assets = data.get("assets", [])

                # Find asset matching envforage-v*-setup.exe or envforage-setup.exe
                installer_url = None
                for asset in assets:
                    name = asset.get("name", "")
                    if name.startswith("envforage-") and name.endswith("-setup.exe"):
                        installer_url = asset.get("browser_download_url")
                        break

                if not installer_url:
                    if interactive:
                        click.echo(
                            "[ERROR] Could not find a Windows GUI setup installer asset in the latest release.",
                            err=True,
                        )
                    return

                # Download to %TEMP%
                import tempfile
                import os

                temp_dir = tempfile.gettempdir()
                installer_name = os.path.basename(installer_url)
                temp_path = os.path.join(temp_dir, installer_name)

                if interactive:
                    click.echo(f"Downloading installer: {installer_name}...")

                with client.stream("GET", installer_url) as r:
                    r.raise_for_status()
                    try:
                        total = int(r.headers.get("content-length", "0"))
                    except (TypeError, ValueError):
                        total = 0
                    downloaded = 0
                    with open(temp_path, "wb") as f:
                        for chunk in r.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if interactive and total > 0:
                                pct = int(downloaded * 100 / total)
                                bar_len = 30
                                filled = int(bar_len * downloaded / total)
                                bar = "#" * filled + "-" * (bar_len - filled)
                                click.echo(
                                    f"\r  [{bar}] {pct}% ({downloaded}/{total} bytes)",
                                    nl=False,
                                    err=True,
                                )
                    if interactive and total > 0:
                        click.echo(err=True)

                if interactive:
                    click.echo("Launching installer in the background and exiting...")

                # Execute installer silently
                kwargs = {}
                if hasattr(subprocess, "DETACHED_PROCESS"):
                    kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

                subprocess.Popen(
                    [temp_path, "/SILENT", "/SUPPRESSMSGBOXES", "/FORCECLOSEAPPLICATIONS"],
                    **kwargs
                )
                sys.exit(0)

        except Exception as e:
            if interactive:
                click.echo(f"[ERROR] Upgrade failed: {e}", err=True)
            return
    else:
        if interactive:
            click.echo("Upgrading envforage pip package...")
        try:
            if interactive:
                proc = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "envforage"])
                if proc.returncode == 0:
                    click.echo("Successfully upgraded envforage pip package.")
                else:
                    click.echo("[ERROR] pip install upgrade command failed.", err=True)
            else:
                subprocess.Popen([sys.executable, "-m", "pip", "install", "--upgrade", "envforage"])
        except Exception as e:
            if interactive:
                click.echo(f"[ERROR] Pip upgrade failed: {e}", err=True)
