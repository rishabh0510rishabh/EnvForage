"""
envforge CLI — main command group and subcommands.

Commands:
  envforge diagnose   Collect and display a DiagnosticReport
  envforge verify     Check if a profile is compatible with this system
  envforge fix        Generate a repair script from a saved report
  envforge rollback   Restore a venv from a backup directory
"""

from __future__ import annotations

import json
import sys
import platform
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box

from envforge_agent import __version__
from envforge_agent.report import ReportBuilder
from envforge_agent.schemas import DiagnosticReport

from envforge_agent.utils import _map_os_to_target, _extract_python_version
from envforge_agent.audit import audit_command

console = Console()
err_console = Console(stderr=True, style="bold red")


def check_macos_support():
    if platform.system() == "Darwin":
        err_console.print("[ERROR] EnvForge is not currently supported on macOS.")
        err_console.print("  Hint: This tool is designed for Linux and Windows (WSL) environments.")
        sys.exit(1)


# ── Root command group ─────────────────────────────────────────────────────────


@click.group()
@click.version_option(__version__, prog_name="envforge-agent")
def cli() -> None:
    """EnvForge CLI Diagnostic Agent — inspect your ML environment."""
    check_macos_support()


# ── envforge diagnose ──────────────────────────────────────────────────────────


@cli.command("diagnose")
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Save report to a JSON file instead of printing to stdout.",
)
@click.option(
    "--send",
    is_flag=True,
    default=False,
    help="Send the report to the EnvForge API for compatibility analysis.",
)
@click.option(
    "--api-url",
    default="http://localhost:8000",
    show_default=True,
    envvar="ENVFORGE_API_URL",
    help="Base URL of the EnvForge API.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress all output except the JSON report.",
)
@click.option(
    "--sarif",
    is_flag=True,
    default=False,
    help="Output diagnostics in SARIF 2.1.0 format for CI/CD pipeline integrations.",
)

@click.option(
    "--timeout", "-t",
    type=int,
    default=30,
    show_default=True,
    help="Timeout in seconds for each detector subprocess call. Default: 30s.",
)

def diagnose(output: str | None, send: bool, api_url: str, quiet: bool, sarif: bool, timeout: int) -> None:
    """
    Collect a full diagnostic report of this machine's ML environment.

    Detects: OS, CPU, RAM, GPU, CUDA, cuDNN, Python installations.
    Outputs: DiagnosticReport JSON compatible with POST /api/v1/diagnose.
    """
    if not quiet:
        console.print(
            Panel(
                f"[bold cyan]EnvForge Diagnostic Agent[/] v{__version__}\n"
                "[dim]Scanning your environment...[/]",
                expand=False,
            )
        )

    report = ReportBuilder(timeout=timeout).build()

    if not quiet:
        _print_report_summary(report)

    # ── SARIF output ────────────────────────────────────────────────────────
    if sarif:
        import json as _json

        click.echo(_json.dumps(report.to_sarif(), indent=2))
        return

    report_json = report.to_json(indent=2)

    # ── Output to file ──────────────────────────────────────────────────────
    if output:
        Path(output).write_text(report_json, encoding="utf-8")
        if not quiet:
            console.print(f"\n[green][+][/] Report saved to [bold]{output}[/]")
    elif not send:
        # Print JSON to stdout (pipe-friendly)
        click.echo(report_json)

    # ── Send to API ─────────────────────────────────────────────────────────
    if send:
        _send_report(report, api_url, quiet)


def _print_report_summary(report: DiagnosticReport) -> None:
    """Print a human-readable summary table to the terminal."""
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    table.add_column("Category", style="bold cyan", width=14)
    table.add_column("Value")

    table.add_row("OS", f"{report.os.name} {report.os.version} ({report.os.architecture})")
    if report.os.wsl_version:
        table.add_row("WSL", report.os.wsl_version)

    cpu_str = f"{report.cpu.brand} — {report.cpu.cores}C / {report.cpu.threads}T"
    if report.cpu.cores < 4:
        cpu_str += "  [yellow]⚠ WARNING: Under 4 cores — data loading may bottleneck training[/]"
    table.add_row("CPU", cpu_str)

    ram_str = f"{report.ram.total_gb} GB total, {report.ram.available_gb} GB free"
    if report.ram.total_gb < 8:
        ram_str += "  [bold red][!] CRITICAL: Under 8 GB — heavy ML profiles will fail[/]"
    elif report.ram.total_gb < 16:
        ram_str += "  [yellow][!] WARNING: Under 16 GB — some ML profiles may be slow[/]"
    table.add_row("RAM", ram_str)

    if report.gpus:
        for gpu in report.gpus:
            vram = f"{gpu.vram_gb} GB" if gpu.vram_gb else "?"
            driver = gpu.driver_version or "?"
            table.add_row("GPU", f"{gpu.name} ({vram} VRAM, driver {driver})")
    else:
        table.add_row("GPU", "[dim]No NVIDIA GPU detected[/]")

    if report.cuda.version:
        cuda_display = report.cuda.version
        if report.cuda.cudnn_version:
            cuda_display += f"  |  cuDNN: {report.cuda.cudnn_version}"
        if report.cuda.nccl_version:
            cuda_display += f"  |  NCCL: {report.cuda.nccl_version}"
        table.add_row("CUDA", cuda_display)
        if report.cuda.toolkit_path:
            table.add_row("CUDA Path", report.cuda.toolkit_path)
    else:
        table.add_row("CUDA", "[dim]Not detected[/]")

    if report.rocm.version:
        gcn = f" (GCN {report.rocm.gcn_arch})" if report.rocm.gcn_arch else ""
        table.add_row("ROCm", f"{report.rocm.version}{gcn}")
    else:
        table.add_row("ROCm", "[dim]Not detected[/]")

    if report.active_python:
        py = report.active_python
        venv = " [dim](venv)[/]" if py.is_venv else ""
        table.add_row("Python", f"{py.version} at {py.path}{venv}")

    if len(report.python_installations) > 1:
        others = [
            p
            for p in report.python_installations
            if p.path != (report.active_python.path if report.active_python else "")
        ]
        if others:
            table.add_row(
                "Other Pythons",
                ", ".join(f"{p.version} ({p.path})" for p in others[:3]),
            )

    console.print(table)


def _send_report(report: DiagnosticReport, api_url: str, quiet: bool) -> None:
    """POST the DiagnosticReport to the EnvForge API."""
    url = f"{api_url.rstrip('/')}/api/v1/diagnose"
    if not quiet:
        console.print(f"\n[bold]Sending report to[/] {url} ...")

    try:
        response = httpx.post(
            url,
            content=report.to_json(),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        if not quiet:
            _print_diagnose_response(result)
        else:
            click.echo(json.dumps(result, indent=2))

    except httpx.ConnectError:
        err_console.print(f"[ERROR] Cannot connect to {url}")
        err_console.print("  Hint: Is the EnvForge API running? Check ENVFORGE_API_URL.")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        err_console.print(f"[ERROR] API returned {e.response.status_code}")
        err_console.print(e.response.text)
        sys.exit(1)


def _print_diagnose_response(result: dict) -> None:
    """Pretty-print the API diagnose response."""
    console.print("\n[bold green][+] Compatibility Analysis[/]")

    if result.get("compatible_profiles"):
        console.print(f"  Compatible profiles: {', '.join(result['compatible_profiles'])}")

    if result.get("recommendations"):
        console.print("\n[bold]Recommendations:[/]")
        for rec in result["recommendations"]:
            console.print(f"  - {rec}")

    if result.get("issues"):
        console.print("\n[bold yellow]Issues:[/]")
        for issue in result["issues"]:
            sev = issue.get("severity", "INFO")
            color = {"ERROR": "red", "WARNING": "yellow", "INFO": "cyan"}.get(sev, "white")
            console.print(f"  [{color}][{sev}][/] {issue['message']}")
            if issue.get("suggested_fix"):
                console.print(f"    Fix: {issue['suggested_fix']}")

    console.print(f"\n  Report ID: {result.get('report_id', '?')}")


# ── envforge verify ────────────────────────────────────────────────────────────


@cli.command("verify")
@click.option(
    "--profile",
    "-p",
    required=False,
    help="Profile slug to verify against (e.g. pytorch-cuda).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Save verification report to a JSON file instead of printing to stdout.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress all output except the JSON verification report.",
)
def verify(profile: str | None, output: str | None, quiet: bool) -> None:
    """
    Verify whether the generated ML environment works after setup.

    Checks PyTorch import and, if a GPU profile is detected, CUDA availability.
    Returns a structured PASS/FAIL JSON result.
    """
    if not quiet:
        console.print(
            Panel(
                f"[bold cyan]EnvForge Verification Agent[/] v{__version__}\n"
                "[dim]Running framework sanity checks...[/]",
                expand=False,
            )
        )

    import subprocess

    # 1. Determine active Python
    report = ReportBuilder().build()
    active_py = report.active_python
    py_executable = active_py.path if active_py else sys.executable

    # 2. Run inline Python script to test torch import and CUDA
    inspector_script = (
        "import sys\n"
        "import json\n"
        "result = {'import_ok': False, 'cuda_ok': False, 'error': None}\n"
        "try:\n"
        "    import torch\n"
        "    result['import_ok'] = True\n"
        "    result['torch_version'] = torch.__version__\n"
        "    try:\n"
        "        result['cuda_ok'] = torch.cuda.is_available()\n"
        "        result['cuda_version'] = torch.version.cuda\n"
        "    except Exception as e:\n"
        "        result['cuda_ok'] = False\n"
        "except Exception as e:\n"
        "    result['import_ok'] = False\n"
        "    result['error'] = f'{type(e).__name__}: {str(e)}'\n"
        "print(json.dumps(result))\n"
    )

    try:
        proc = subprocess.run(
            [py_executable, "-c", inspector_script], capture_output=True, text=True, timeout=15
        )
        if proc.returncode != 0:
            res = {
                "status": "FAIL",
                "message": "Python verification script failed to execute",
                "error": proc.stderr.strip() or f"Exit code {proc.returncode}",
            }
            click.echo(json.dumps(res, indent=2))
            sys.exit(1)

        data = json.loads(proc.stdout.strip())

        # 3. Analyze checks
        if not data["import_ok"]:
            if not quiet:
                _print_verification_summary(data, is_gpu_profile=False)
            res = {
                "status": "FAIL",
                "message": "PyTorch import failed — is it installed?",
                "error": data["error"],
            }
            click.echo(json.dumps(res, indent=2))
            sys.exit(1)

        # Check if CUDA profile is detected
        is_gpu_profile = False
        if profile:
            is_gpu_profile = any(
                term in profile.lower() for term in ["cuda", "gpu", "diffusion", "finetune"]
            )

        if is_gpu_profile and not data["cuda_ok"]:
            if not quiet:
                _print_verification_summary(data, is_gpu_profile=is_gpu_profile)
            res = {
                "status": "FAIL",
                "message": "PyTorch installed but CUDA not available",
                "error": "torch.cuda.is_available() returned False",
            }
            click.echo(json.dumps(res, indent=2))
            sys.exit(1)

        # All required checks passed!
        msg = "Environment works: PyTorch imported successfully"
        if data["cuda_ok"]:
            msg += " with CUDA support"
        else:
            msg += " (CPU only)"

        if not quiet:
            _print_verification_summary(data, is_gpu_profile=is_gpu_profile)

        res = {"status": "PASS", "message": msg}
        click.echo(json.dumps(res, indent=2))
        sys.exit(0)

    except subprocess.TimeoutExpired:
        res = {
            "status": "FAIL",
            "message": "Verification timed out",
            "error": "Subprocess took longer than 15 seconds",
        }
        click.echo(json.dumps(res, indent=2))
        sys.exit(1)
    except Exception as e:
        res = {
            "status": "FAIL",
            "message": "Verification failed due to an unexpected error",
            "error": str(e),
        }
        click.echo(json.dumps(res, indent=2))
        sys.exit(1)


def _print_verification_summary(data: dict, is_gpu_profile: bool) -> None:
    """Print a beautiful human-readable verification matrix to the terminal."""
    table = Table(box=box.ROUNDED, show_header=True, padding=(0, 1))
    table.add_column("Check Matrix", style="bold cyan", width=22)
    table.add_column("Status", width=12, justify="center")
    table.add_column("Details")

    # PyTorch import check
    if data.get("import_ok"):
        torch_v = data.get("torch_version", "Unknown")
        table.add_row(
            "PyTorch Core Import", "[bold green]PASS[/]", f"Framework loaded cleanly (v{torch_v})."
        )
    else:
        table.add_row("PyTorch Core Import", "[bold red]FAIL[/]", f"[red]{data.get('error')}[/]")

    # CUDA compute engine check
    if data.get("cuda_ok"):
        table.add_row(
            "CUDA Compute Engine", "[bold green]PASS[/]", "Graphics hardware handshake succeeded."
        )
    else:
        # If the profile requires GPU but CUDA check failed, mark as FAIL. Otherwise, SKIP.
        if is_gpu_profile:
            table.add_row(
                "CUDA Compute Engine",
                "[bold red]FAIL[/]",
                "[red]Required by profile, but unavailable.[/]",
            )
        else:
            table.add_row(
                "CUDA Compute Engine", "[dim yellow]SKIP[/]", "Running on native CPU space."
            )
    cuda_v = data.get("cuda_version") or "Not Detected"
    table.add_row("Installed CUDA Version", "[dim]INFO[/]", f"{cuda_v}")

    table.add_row("Required CUDA Profile", "[dim]INFO[/]", ">= 11.8 (Recommended for CUDA paths)")

    console.print("\n[bold]=== Verification Report ===[/]")
    console.print(table)


# ── envforge fix ───────────────────────────────────────────────────────────────


@cli.command("fix")
@click.option(
    "--report",
    "-r",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
    help="Path to a saved DiagnosticReport JSON file.",
)
@click.option(
    "--profile",
    "-p",
    required=True,
    help="Profile slug to generate a repair script for.",
)
@click.option(
    "--api-url",
    default="http://localhost:8000",
    show_default=True,
    envvar="ENVFORGE_API_URL",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview the names of the scripts and resolved packages without printing their full contents.",
)
def fix(report: str, profile: str, api_url: str, dry_run: bool) -> None:
    """
    Generate a repair script based on a saved diagnostic report.

    Sends the report to the API and requests a setup script for the target profile.
    """
    console.print(f"[bold cyan]Generating repair script[/] for profile: {profile}")

    try:
        raw = Path(report).read_text(encoding="utf-8")
        parsed = DiagnosticReport.model_validate_json(raw)
    except Exception as e:
        err_console.print(f"Failed to parse report file: {e}")
        sys.exit(1)

    # Detect OS and Python from the loaded report to build a generate request
    target_os = _map_os_to_target(parsed)
    python_version = _extract_python_version(parsed)

    url = f"{api_url.rstrip('/')}/api/v1/scripts/generate"
    payload = {
        "profile_id": profile,
        "target_os": target_os,
        "python_version": python_version,
        "cuda_version": parsed.cuda.version,
        "output_formats": ["setup.sh"] if target_os != "WIN" else ["setup.ps1", "requirements.txt"],
    }

    try:
        response = httpx.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        console.print(f"[green][+][/] Scripts generated (job: {result.get('job_id', '?')})")

        if result.get("resolved_packages"):
            console.print(f"  [cyan]Resolved Packages:[/] {', '.join(result['resolved_packages'])}")

        if dry_run:
            console.print("\n[bold]Files to be generated:[/]")
            for script in result.get("scripts", []):
                console.print(f"  - {script['filename']}")
        else:
            for script in result.get("scripts", []):
                console.print(
                    Panel(
                        Syntax(script["content"], "bash", theme="monokai", line_numbers=True),
                        title=f"[bold]{script['filename']}[/]",
                    )
                )

        download_url = f"{api_url.rstrip('/')}{result.get('download_url', '')}"
        console.print(f"\n  Download all: [link={download_url}]{download_url}[/link]")

    except httpx.ConnectError:
        err_console.print(f"Cannot connect to {url}. Is the API running?")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        err_console.print(f"API error {e.response.status_code}: {e.response.text}")
        sys.exit(1)

cli.add_command(audit_command)
# ── envforge rollback ──────────────────────────────────────────────────────────

@cli.command("rollback")
def rollback() -> None:
    """
    Restore a virtual environment from a backup created by repair_venv_recreate.

    Scans the current directory for folders matching *_backup_* and prompts
    the user to select one to restore via Rich interactive prompt.
    """
    import glob
    import shutil
    import os

    def _is_venv_backup(p: str) -> bool:
        path = Path(p)
        return path.is_dir() and (path / "pyvenv.cfg").exists()

    backups = sorted(
        p
        for p in (glob.glob("*_backup_*") + glob.glob(".*_backup_*"))
        if _is_venv_backup(p)
    )

    if not backups:
        err_console.print("[ERROR] No backup directories found in the current directory.")
        err_console.print("  Hint: Backups are created by 'envforge fix' and named like '.venv_backup_20260524'.")
        sys.exit(1)

    console.print(Panel(
        f"[bold cyan]EnvForge Rollback[/] v{__version__}\n"
        "[dim]Restoring virtual environment from backup...[/]",
        expand=False,
    ))

    table = Table(box=box.ROUNDED, show_header=True, padding=(0, 1))
    table.add_column("#", style="bold cyan", width=4)
    table.add_column("Backup Directory", style="bold")

    for i, b in enumerate(backups, start=1):
        table.add_row(str(i), b)

    console.print(table)

    if len(backups) == 1:
        chosen = backups[0]
        console.print(f"[dim]Only one backup found — selecting:[/] [bold]{chosen}[/]")
    else:
        from rich.prompt import IntPrompt
        idx = IntPrompt.ask(
            "Select backup number to restore",
            choices=[str(i) for i in range(1, len(backups) + 1)],
        )
        chosen = backups[idx - 1]

    chosen_path = Path(chosen)
    chosen_name = chosen_path.name
    if "_backup_" not in chosen_name:
        err_console.print(f"[ERROR] Invalid backup folder name structure: {chosen}")
        sys.exit(1)

    parts = chosen_name.rsplit("_backup_", 1)
    original_name = parts[0]
    if not original_name:
        err_console.print(f"[ERROR] Could not determine original virtual environment name: {chosen_name}")
        sys.exit(1)

    original = str(chosen_path.with_name(original_name))

    console.print(f"\n[yellow]This will replace '[bold]{original}[/]' with '[bold]{chosen}[/]'[/]")

    from rich.prompt import Confirm
    if not Confirm.ask("Proceed with rollback?"):
        console.print("[dim]Rollback cancelled.[/]")
        sys.exit(0)

    temp_original = None
    original_path = Path(original)
    try:
        if original_path.exists():
            temp_original = Path(str(original_path) + f"_rollback_tmp_{os.getpid()}")
            if temp_original.exists():
                shutil.rmtree(temp_original)
            original_path.rename(temp_original)

        shutil.copytree(chosen, original)
        
        if temp_original and temp_original.exists():
            shutil.rmtree(temp_original)
            
        console.print(f"\n[green][+][/] Rollback complete. '[bold]{original}[/]' restored from '[bold]{chosen}[/]'")

    except Exception as e:
        if temp_original and temp_original.exists():
            try:
                if original_path.exists():
                    shutil.rmtree(original_path)
                temp_original.rename(original_path)
            except Exception as restore_err:
                err_console.print(f"[WARNING] Failed to restore original directory: {restore_err}")
        elif original_path.exists():
            shutil.rmtree(original_path, ignore_errors=True)
        err_console.print(f"[ERROR] Rollback failed: {e}")
        sys.exit(1)
