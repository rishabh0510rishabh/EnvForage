"""
envforage CLI — main command group and subcommands.

Commands:
  envforage diagnose    Collect and display a DiagnosticReport
  envforage verify     Check if a profile is compatible with this system
  envforage fix         Generate a repair script from a saved report
  envforage rollback   Restore a venv from a backup directory
"""

from __future__ import annotations

import json
import sys
import platform
from pathlib import Path
import asyncio
import urllib.parse

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box

from envforage import __version__
from envforage.report import ReportBuilder
from envforage.schemas import DiagnosticReport
from envforage.detectors import detect_wsl_gpu_passthrough

from envforage.utils import _map_os_to_target, _extract_python_version, check_for_updates, run_upgrade
from envforage.audit import audit_command
from envforage.config import load_config

console = Console()
err_console = Console(stderr=True, style="bold red")


def _reinit_consoles(no_color: bool) -> None:
    """Reinitialise global consoles with no-color mode if requested."""
    global console, err_console
    if no_color:
        console = Console(no_color=True, highlight=False)
        err_console = Console(stderr=True, no_color=True, highlight=False)


def _handle_api_status_error(e: httpx.HTTPStatusError) -> None:
    """Pretty print HTTPStatusError response payloads from the backend."""
    try:
        err_data = e.response.json()
        detail = err_data.get("detail", {})
        error_info = detail.get("error", {})
        if error_info:
            msg = error_info.get("message", "")
            code = error_info.get("code", "")
            details = error_info.get("details", {})

            group_items = [
                f"[bold red]Error Code:[/] {code}",
                f"[bold red]Description:[/] {msg}",
            ]
            if details:
                if "component" in details:
                    group_items.append(f"[bold red]Component:[/] {details['component']}")
                if "constraint" in details:
                    group_items.append(f"[bold red]Constraint:[/] {details['constraint']}")
                if "detected" in details:
                    group_items.append(f"[bold red]Detected:[/] {details['detected']}")
                if "suggestion" in details:
                    group_items.append(f"[bold green]Suggestion:[/] {details['suggestion']}")
                if "docs_url" in details:
                    group_items.append(f"[bold]Documentation:[/] [link={details['docs_url']}]{details['docs_url']}[/link]")

            panel = Panel(
                "\n".join(group_items),
                title=f"[bold red]Compatibility Engine Conflict ({e.response.status_code})[/]",
                border_style="red"
            )
            err_console.print(panel)
        else:
            err_console.print(f"[ERROR] API returned {e.response.status_code}: {e.response.text}")
    except Exception:
        err_console.print(f"[ERROR] API returned {e.response.status_code}: {e.response.text}")
    sys.exit(1)


def check_macos_support():
    if platform.system() == "Darwin":
        err_console.print("[ERROR] EnvForage is not currently supported on macOS.")
        err_console.print("  Hint: This tool is designed for Linux and Windows (WSL) environments.")
        sys.exit(1)


# ── Root command group ─────────────────────────────────────────────────────────


def _version_callback(ctx: click.Context, _param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    python_ver = sys.version.split()[0]
    os_info = f"{platform.system()} {platform.release()} {platform.machine()}"
    click.echo(f"envforage {__version__}")
    click.echo(f"Python {python_ver} · {os_info}")
    ctx.exit()


def _upgrade_callback(ctx: click.Context, _param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    run_upgrade(interactive=True)
    ctx.exit()


@click.group()
@click.option(
    "--version",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_version_callback,
    help="Show the version and exit.",
)
@click.option(
    "--upgrade",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_upgrade_callback,
    help="Upgrade EnvForage CLI to the latest version.",
)
@click.option(
    "--no-color",
    is_flag=True,
    default=False,
    envvar="NO_COLOR",
    help="Disable colour and Rich markup in all output. Useful for CI pipelines.",
)
@click.pass_context
def cli(ctx: click.Context, no_color: bool) -> None:
    """EnvForage CLI Diagnostic Agent — inspect your ML environment."""
    ctx.ensure_object(dict)
    _reinit_consoles(no_color)
    check_macos_support()
    if ctx.invoked_subcommand != "upgrade" and "--upgrade" not in sys.argv:
        check_for_updates()


# ── envforage diagnose ──────────────────────────────────────────────────────────


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
    help="Send the report to the EnvForage API for compatibility analysis.",
)
@click.option(
    "--api-url",
    default=None,
    help="Base URL of the EnvForage API.",
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
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "minimal"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: table (default Rich table), json (structured JSON), minimal (one-liner).",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=None,
    help="Timeout in seconds for each detector subprocess call. Default: 30s.",
)
def diagnose(
    output: str | None,
    send: bool,
    api_url: str | None,
    quiet: bool,
    sarif: bool,
    timeout: int | None,
    output_format: str = "table",
) -> None:
    config = load_config()
    final_api_url = api_url or config.api_url
    if final_api_url and "#" in final_api_url:
        final_api_url = urllib.parse.urldefrag(final_api_url).url.strip()
    final_timeout = timeout or config.timeout
    asyncio.run(_diagnose(output, send, final_api_url, quiet, sarif, final_timeout, output_format))


async def _diagnose(
    output: str | None,
    send: bool,
    api_url: str,
    quiet: bool,
    sarif: bool,
    timeout: int,
    output_format: str,
) -> None:
    """
    Collect a full diagnostic report of this machine's ML environment.
    """
    if not quiet:
        console.print(
            Panel(
                f"[bold cyan]EnvForage Diagnostic Agent[/] v{__version__}\n"
                "[dim]Scanning your environment...[/]",
                expand=False,
            )
        )

    report = ReportBuilder(timeout=timeout).build()

    if report.os.wsl_version == "WSL2":
        wsl_gpu_ok, wsl_gpu_issues = detect_wsl_gpu_passthrough(timeout=timeout)
        if not wsl_gpu_ok and not quiet:
            click.echo(
                "[!] GPU passthrough unavailable in WSL2. Falling back to CPU environment recommendation."
            )
            for issue in wsl_gpu_issues:
                click.echo(f"  - {issue}")

    if not quiet:
        _print_report_summary(report)
        _print_recommendations(report)

    # ── SARIF output ────────────────────────────────────────────────────────
    if sarif:
        import json as _json

        click.echo(_json.dumps(report.to_sarif(), indent=2))
        return

    if send and output_format not in ("json", "table"):
        err_console.print(
            f"[ERROR] --send requires JSON format; --format {output_format} is incompatible."
        )
        err_console.print("  Hint: Use --format json or drop --send.")
        sys.exit(1)

    if output_format == "minimal":
        report_output = (
            f"OS={report.os.name} {report.os.version} | "
            f"CPU={report.cpu.cores}C/{report.cpu.threads}T | "
            f"RAM={report.ram.total_gb}GB | "
            f"GPU={'None' if not report.gpus else report.gpus[0].name} | "
            f"CUDA={report.cuda.version or 'None'} | "
            f"Python={report.active_python.version if report.active_python else 'None'}"
        )
    else:  # table or json both save/echo as JSON
        report_output = report.to_json(indent=2)

    # ── Output to file ──────────────────────────────────────────────────────
    if output:
        Path(output).write_text(report_output, encoding="utf-8")
        if not quiet:
            console.print(f"\n[green][+][/] Report saved to [bold]{output}[/]")
    elif not send and output_format != "table":
        click.echo(report_output)

    # ── Send to API ─────────────────────────────────────────────────────────
    if send:
        await _send_report(report, api_url, quiet)


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

    disk_str = f"{report.disk.available_gb:.1f} GB free of {report.disk.total_gb:.1f} GB"
    if report.disk.available_gb < 5:
        disk_str += "  [bold red]⚠ CRITICAL: Under 5 GB — setup will likely fail[/]"
    elif report.disk.available_gb < 20:
        disk_str += "  [yellow]⚠ WARNING: Low disk space — GPU profiles need 20+ GB[/]"
    table.add_row("Disk Free", disk_str)

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
        py_str = f"{py.version} at {py.path}{venv}"
        if py.is_venv:
            py_str += (
                "  [yellow]⚠ Running inside a venv — CUDA detection via torch "
                "may be inaccurate if torch is not installed in this environment.[/]"
            )
        table.add_row("Python", py_str)

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


def _print_recommendations(report: DiagnosticReport) -> None:
    """Print ML framework recommendations based on detected hardware."""
    warnings: list[str] = []
    profiles: list[tuple[str, str]] = []

    has_gpu = len(report.gpus) > 0
    vrams = [gpu.vram_gb for gpu in report.gpus if gpu.vram_gb is not None]
    max_vram = max(vrams) if vrams else None
    total_ram = report.ram.total_gb

    os_name = report.os.name.lower()
    cpu_brand = report.cpu.brand.lower()
    is_macos = "macos" in os_name or "darwin" in os_name or "mac os" in os_name
    is_arm_apple = (
        "apple" in cpu_brand
        or "m1" in cpu_brand
        or "m2" in cpu_brand
        or "m3" in cpu_brand
        or "m4" in cpu_brand
    )
    is_apple_silicon = is_macos and is_arm_apple

    if total_ram < 8:
        warnings.append(
            "Low system RAM (<8 GB) — heavy ML workloads may fail. Consider cpu-only profiles."
        )

    if is_apple_silicon:
        profiles.append(("pytorch-mps", "Apple Silicon — PyTorch MPS backend"))
        profiles.append(("cpu-only", "Fallback for frameworks without MPS support"))
    elif not has_gpu:
        profiles.append(("cpu-only", "No GPU detected — PyTorch CPU, TensorFlow CPU"))
        profiles.append(("sklearn", "Scikit-learn works well on CPU-only systems"))
    elif max_vram is not None and max_vram < 4:
        warnings.append(f"Low GPU VRAM ({max_vram:.1f} GB) — large models will not fit.")
        profiles.append(("yolov8-nano", "Lightweight model for low-VRAM GPUs"))
        profiles.append(("sklearn", "CPU-based ML avoids VRAM limitations"))
    elif max_vram is not None and max_vram <= 8:
        profiles.append(("pytorch-cuda", f"GPU with {max_vram:.1f} GB VRAM — PyTorch CUDA"))
        profiles.append(("yolov8", "YOLOv8 runs well on 4–8 GB VRAM"))
    else:
        vram_str = f"{max_vram:.1f} GB" if max_vram else "high"
        profiles.append(("tf-gpu", f"High-VRAM GPU ({vram_str}) — TensorFlow GPU"))
        profiles.append(("pytorch-cuda", "PyTorch CUDA for training and research"))
        profiles.append(("yolov8", "YOLOv8 full model variants"))

    console.print("\n[bold cyan]Recommended Profiles:[/]")
    for i, (name, reason) in enumerate(profiles, 1):
        console.print(f"  {i}. [bold]{name}[/] — {reason}")

    if warnings:
        console.print("\n[bold yellow]Warnings:[/]")
        for w in warnings:
            console.print(f"  [yellow]⚠[/] {w}")


async def _send_report(report: DiagnosticReport, api_url: str, quiet: bool) -> None:
    """POST the DiagnosticReport to the EnvForage API with retry logic."""
    url = f"{api_url.rstrip('/')}/api/v1/diagnose"
    if not quiet:
        console.print(f"\n[bold]Sending report to[/] {url} ...")

    max_attempts = 3
    delays = [2, 4]  # seconds between retries

    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
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
            return

        except (httpx.ConnectError, httpx.TimeoutException):
            if attempt < max_attempts:
                delay = delays[attempt - 1]
                if not quiet:
                    console.print(
                        f"  [yellow][Attempt {attempt}/{max_attempts}] "
                        f"Connection failed, retrying in {delay}s...[/]"
                    )
                await asyncio.sleep(delay)
            else:
                err_console.print(f"[ERROR] Cannot connect to {url}")
                err_console.print("  Hint: Is the EnvForage API running? Check ENVFORAGE_API_URL.")
                sys.exit(1)

        except httpx.HTTPStatusError as e:
            _handle_api_status_error(e)


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


# ── envforage verify ────────────────────────────────────────────────────────────


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
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    default=False,
    help="Output only the verification JSON result.",
)
def verify(
    profile: str | None,
    output: str | None,
    quiet: bool,
    json_output: bool,
) -> None: 
    """
    Verify whether the generated ML environment works after setup.

    Checks PyTorch import and, if a GPU profile is detected, CUDA availability.
    Returns a structured PASS/FAIL JSON result.
    """
    if json_output:
        quiet = True
    
    if not quiet and not json_output:
        console.print(
            Panel(
                f"[bold cyan]EnvForage Verification Agent[/] v{__version__}\n"
                "[dim]Running framework sanity checks...[/]",
                expand=False,
            )
        )

    import subprocess

    # 1. Determine active Python
    report = ReportBuilder().build()
    active_py = report.active_python
    py_executable = active_py.path if active_py else sys.executable

    # Determine target framework based on profile
    target_framework = "torch"
    if profile:
        p_lower = profile.lower()
        if "tensorflow" in p_lower or "tf" in p_lower:
            target_framework = "tensorflow"
        elif "jax" in p_lower:
            target_framework = "jax"

    # 2. Run inline Python script to test framework import and CUDA/GPU
    inspector_script = (
        "import sys\n"
        "import json\n"
        "result = {'framework': 'PyTorch', 'import_ok': False, 'version': None, 'cuda_ok': False, 'cuda_version': None, 'error': None}\n"
        f"target = '{target_framework}'\n"
        "try:\n"
        "    if target == 'tensorflow':\n"
        "        import tensorflow as tf\n"
        "        result['framework'] = 'TensorFlow'\n"
        "        result['import_ok'] = True\n"
        "        result['version'] = tf.__version__\n"
        "        gpus = tf.config.list_physical_devices('GPU')\n"
        "        result['cuda_ok'] = len(gpus) > 0\n"
        "        try:\n"
        "            from tensorflow.python.platform import build_info as tf_build_info\n"
        "            result['cuda_version'] = tf_build_info.build_info.get('cuda_version', 'unknown')\n"
        "        except Exception:\n"
        "            pass\n"
        "    elif target == 'jax':\n"
        "        import jax\n"
        "        result['framework'] = 'JAX'\n"
        "        result['import_ok'] = True\n"
        "        result['version'] = jax.__version__\n"
        "        try:\n"
        "            devices = jax.devices()\n"
        "            result['cuda_ok'] = any(d.platform == 'gpu' for d in devices)\n"
        "            try:\n"
        "                import jaxlib\n"
        "                result['cuda_version'] = getattr(jaxlib, '__version__', 'unknown')\n"
        "            except Exception:\n"
        "                pass\n"
        "        except Exception as e:\n"
        "            result['cuda_ok'] = False\n"
        "            result['error'] = f'JAX devices call failed: {str(e)}'\n"
        "    else:\n"
        "        import torch\n"
        "        result['framework'] = 'PyTorch'\n"
        "        result['import_ok'] = True\n"
        "        result['version'] = torch.__version__\n"
        "        result['cuda_ok'] = torch.cuda.is_available()\n"
        "        result['cuda_version'] = torch.version.cuda\n"
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
        framework_name = data.get("framework", "PyTorch")
        if not data["import_ok"]:
            if not quiet and not json_output:
                _print_verification_summary(data, is_gpu_profile=False)
            res = {
                "status": "FAIL",
                "message": f"{framework_name} import failed — is it installed?",
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
            if not quiet and not json_output:
                _print_verification_summary(data, is_gpu_profile=is_gpu_profile)
            res = {
                "status": "FAIL",
                "message": f"{framework_name} installed but CUDA not available",
                "error": "GPU device check returned False",
            }
            click.echo(json.dumps(res, indent=2))
            sys.exit(1)

        # All required checks passed!
        msg = f"Environment works: {framework_name} imported successfully"
        if data["cuda_ok"]:
            msg += " with CUDA support"
        else:
            msg += " (CPU only)"

        if not quiet and not json_output:
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

    framework = data.get("framework", "PyTorch")
    version = data.get("version", "Unknown")

    # Core import check
    if data.get("import_ok"):
        table.add_row(
            f"{framework} Core Import", "[bold green]PASS[/]", f"Framework loaded cleanly (v{version})."
        )
    else:
        table.add_row(f"{framework} Core Import", "[bold red]FAIL[/]", f"[red]{data.get('error')}[/]")

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


# ── envforage fix ───────────────────────────────────────────────────────────────


@cli.command("fix")
@click.option(
    "--report",
    "-r",
    type=click.Path(dir_okay=False, readable=True),
    required=True,
    help="Path to a saved DiagnosticReport JSON file.",
)
@click.option(
    "--profile",
    "-p",
    required=False,
    default=None,
    help="Profile slug to generate a repair script for.",
)
@click.option(
    "--api-url",
    default=None,
    help="Base URL of the EnvForage API.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview the names of the scripts and resolved packages without printing their full contents.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress all logging output and print only the generated script contents.",
)
def fix(report: str, profile: str | None, api_url: str | None, dry_run: bool, quiet: bool) -> None:
    config = load_config()
    final_api_url = api_url or config.api_url
    asyncio.run(_fix(report, profile, final_api_url, dry_run, quiet))


def _get_recommended_profiles(report: DiagnosticReport) -> list[str]:
    """Helper to get recommended profile slugs based on hardware scan."""
    has_gpu = len(report.gpus) > 0
    vrams = [gpu.vram_gb for gpu in report.gpus if gpu.vram_gb is not None]
    max_vram = max(vrams) if vrams else None

    os_name = report.os.name.lower()
    cpu_brand = report.cpu.brand.lower()
    is_macos = "macos" in os_name or "darwin" in os_name or "mac os" in os_name
    is_arm_apple = (
        "apple" in cpu_brand
        or "m1" in cpu_brand
        or "m2" in cpu_brand
        or "m3" in cpu_brand
        or "m4" in cpu_brand
    )
    is_apple_silicon = is_macos and is_arm_apple

    if is_apple_silicon:
        return ["pytorch-mps", "cpu-only"]
    if not has_gpu:
        return ["cpu-only", "sklearn"]
    if max_vram is not None and max_vram < 4:
        return ["yolov8-nano", "sklearn"]
    if max_vram is not None and max_vram <= 8:
        return ["pytorch-cuda", "yolov8"]
    return ["tf-gpu", "pytorch-cuda", "yolov8"]


async def _fix(report: str, profile: str | None, api_url: str, dry_run: bool, quiet: bool) -> None:
    """
    Generate a repair script based on a saved diagnostic report.

    Sends the report to the API and requests a setup script for the target profile.
    """
    try:
        raw = Path(report).read_text(encoding="utf-8")
        parsed = DiagnosticReport.model_validate_json(raw)
    except Exception as e:
        err_console.print(f"Failed to parse report file: {e}")
        sys.exit(1)

    if not profile:
        recommended = _get_recommended_profiles(parsed)
        if not recommended:
            recommended = ["cpu-only"]

        if sys.stdin.isatty():
            console.print("[bold cyan]Please select a profile to generate the repair script for:[/]")
            for i, p in enumerate(recommended, 1):
                console.print(f"  {i}. [bold]{p}[/]")
            try:
                choice = click.prompt("Select profile index", type=int, default=1, err=True)
                if 1 <= choice <= len(recommended):
                    profile = recommended[choice - 1]
                else:
                    profile = recommended[0]
            except Exception:
                profile = recommended[0]
        else:
            profile = recommended[0]

    if not quiet:
        console.print(f"[bold cyan]Generating repair script[/] for profile: {profile}")

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
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        if not quiet:
            console.print(f"[green][+][/] Scripts generated (job: {result.get('job_id', '?')})")

        if result.get("resolved_packages") and not quiet:
            console.print(f"  [cyan]Resolved Packages:[/] {', '.join(result['resolved_packages'])}")

        if dry_run:
            if not quiet:
                console.print("\n[bold]Files to be generated:[/]")
            for script in result.get("scripts", []):
                if quiet:
                    click.echo(script["filename"])
                else:
                    console.print(f"  - {script['filename']}")
        else:
            for script in result.get("scripts", []):
                if quiet:
                    click.echo(script["content"])
                else:
                    console.print(
                        Panel(
                            Syntax(script["content"], "bash", theme="monokai", line_numbers=True),
                            title=f"[bold]{script['filename']}[/]",
                        )
                    )

        if not quiet:
            download_url = f"{api_url.rstrip('/')}{result.get('download_url', '')}"
            console.print(f"\n  Download all: [link={download_url}]{download_url}[/link]")

    except httpx.ConnectError:
        err_console.print(f"Cannot connect to {url}. Is the API running?")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        _handle_api_status_error(e)


@cli.command("upgrade")
def upgrade() -> None:
    """Upgrade EnvForage CLI to the latest version."""
    run_upgrade(interactive=True)


cli.add_command(audit_command)


# ── envforage rollback ──────────────────────────────────────────────────────────


@cli.command("rollback")
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress all logging output and display minimal prompts.",
)
def rollback(quiet: bool) -> None:
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
        p for p in (glob.glob("*_backup_*") + glob.glob(".*_backup_*")) if _is_venv_backup(p)
    )

    if not backups:
        err_console.print("[ERROR] No backup directories found in the current directory.")
        err_console.print(
            "  Hint: Backups are created by 'envforage fix' and named like '.venv_backup_20260524'."
        )
        sys.exit(1)

    if not quiet:
        console.print(
            Panel(
                f"[bold cyan]EnvForage Rollback[/] v{__version__}\n"
                "[dim]Restoring virtual environment from backup...[/]",
                expand=False,
            )
        )

    table = Table(box=box.ROUNDED, show_header=True, padding=(0, 1))
    table.add_column("#", style="bold cyan", width=4)
    table.add_column("Backup Directory", style="bold")

    for i, b in enumerate(backups, start=1):
        table.add_row(str(i), b)

    if not quiet:
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
        err_console.print(
            f"[ERROR] Could not determine original virtual environment name: {chosen_name}"
        )
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

        console.print(
            f"\n[green][+][/] Rollback complete. '[bold]{original}[/]' restored from '[bold]{chosen}[/]'"
        )

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


# ── envforage troubleshoot ──────────────────────────────────────────────────────


@cli.command("troubleshoot")
@click.option(
    "--api-url",
    default=None,
    help="Base URL of the EnvForage API.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress all logging output and print only the analysis results.",
)
def troubleshoot(api_url: str | None, quiet: bool) -> None:
    config = load_config()
    final_api_url = api_url or config.api_url
    asyncio.run(_troubleshoot(final_api_url, quiet))


async def _troubleshoot(api_url: str, quiet: bool) -> None:
    """
    Send diagnostic report to AI troubleshoot endpoint
    and stream analysis results live to terminal.
    """
    if not quiet:
        console.print(
            Panel(
                "[bold cyan]EnvForage AI Troubleshooter[/]\n[dim]Analyzing environment issues...[/]",
                expand=False,
            )
        )

    # Build diagnostic report
    report = ReportBuilder().build()
    url = f"{api_url.rstrip('/')}/api/v1/troubleshoot"

    if not quiet:
        console.print(f"\n[bold]Connecting to[/] {url}\n")

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                url,
                json={
                    "diagnostic": report.model_dump(),
                    "user_description": "CLI troubleshoot request",
                },
                headers={
                    "Accept": "text/event-stream",
                },
                timeout=60,
            ) as response:
                response.raise_for_status()

                if not quiet:
                    console.print("[bold green]AI Troubleshooting Analysis[/]\n")

                # Buffer streamed chunks
                buffer = ""

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # SSE format: data: ...
                    if line.startswith("data: "):
                        chunk = line.removeprefix("data: ")

                        # accumulate streamed fragments
                        buffer += chunk

            try:
                parsed = json.loads(buffer)

                if parsed.get("error"):
                    err_console.print(f"[ERROR] {parsed.get('message', parsed['error'])}")
                    sys.exit(1)

                # Root Cause
                if not quiet:
                    console.print("\n[bold red]Root Cause:[/]")
                console.print(parsed.get("root_cause", "Unknown"))

                # Suggested Fixes
                if parsed.get("suggested_fixes"):
                    if not quiet:
                        console.print("\n[bold yellow]Suggested Fixes:[/]")
                    for fix in parsed["suggested_fixes"]:
                        if quiet:
                            console.print(f"\n{fix['step']}. {fix['title']}")
                            console.print(f"   {fix['description']}")
                            if fix.get("safe_commands"):
                                for cmd in fix["safe_commands"]:
                                    console.print(f"    • {cmd}")
                        else:
                            console.print(f"\n[bold]{fix['step']}.[/] {fix['title']}")
                            console.print(f"   Severity: {fix['severity']}")
                            console.print(f"   {fix['description']}")

                            if fix.get("safe_commands"):
                                console.print("   Commands:")
                                for cmd in fix["safe_commands"]:
                                    console.print(f"    • {cmd}")

                # Confidence
                if parsed.get("confidence") is not None:
                    if not quiet:
                        console.print(f"\n[bold cyan]Confidence:[/] {parsed['confidence']}")
                    else:
                        console.print(f"\nConfidence: {parsed['confidence']}")

                if not quiet:
                    console.print("\n[bold green][+] Troubleshooting complete[/]")

            except json.JSONDecodeError:
                err_console.print("[ERROR] Failed to parse streamed AI response.")
                sys.exit(1)

    except httpx.ConnectError:
        err_console.print(f"[ERROR] Cannot connect to {url}")
        err_console.print("Hint: Make sure the EnvForage backend API is running.")
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        err_console.print(f"[ERROR] API returned {exc.response.status_code}")
        try:
            error_text = exc.response.read().decode()
            err_console.print(error_text)
        except Exception:
            err_console.print("[ERROR] Unable to read error response body.")
        sys.exit(1)
    except KeyboardInterrupt:
        err_console.print("\n[!] Troubleshooting interrupted by user.")
        sys.exit(1)
    except Exception as exc:
        err_console.print(f"[ERROR] Unexpected error: {exc}")
        sys.exit(1)


# ── envforage list ──────────────────────────────────────────────────────────────


@cli.command("list")
@click.option(
    "--api-url",
    default="http://localhost:8000",
    show_default=True,
    envvar="ENVFORAGE_API_URL",
    help="Base URL of the EnvForage API.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress all output except the JSON profile list.",
)
@click.option(
    "--filter",
    "-f",
    "filter_tag",
    default=None,
    help="Filter profiles by tag (e.g. cuda, cpu, diffusion).",
)
def list_profiles(api_url: str, quiet: bool, filter_tag: str | None) -> None:
    """
    List all available environment profiles from the EnvForage API.

    Fetches from GET /api/v1/profiles and displays a formatted summary table.
    Use --filter to narrow results by tag.
    """
    url = f"{api_url.rstrip('/')}/api/v1/profiles"

    if not quiet:
        console.print(
            Panel(
                f"[bold cyan]EnvForage Profile Registry[/] v{__version__}\n"
                "[dim]Fetching available environment profiles...[/]",
                expand=False,
            )
        )

    try:
        profiles: list[dict] = []
        page = 1
        limit = 100

        while True:
            response = httpx.get(url, params={"page": page, "limit": limit}, timeout=15)
            response.raise_for_status()
            data = response.json()

            page_profiles = data.get("profiles", []) if isinstance(data, dict) else data
            if not isinstance(page_profiles, list):
                err_console.print("[ERROR] Invalid profiles payload from API.")
                sys.exit(1)

            profiles.extend(page_profiles)

            total = data.get("total") if isinstance(data, dict) else None
            if not page_profiles or (isinstance(total, int) and len(profiles) >= total):
                break
            page += 1

    except httpx.ConnectError:
        err_console.print(f"[ERROR] Cannot connect to {url}")
        err_console.print("  Hint: Is the EnvForage API running? Check ENVFORAGE_API_URL.")
        sys.exit(1)
    except httpx.RequestError as e:
        err_console.print(f"[ERROR] Request failed for {url}: {e}")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        err_console.print(f"[ERROR] API returned {e.response.status_code}")
        err_console.print(e.response.text)
        sys.exit(1)
    except ValueError:
        err_console.print("[ERROR] API returned invalid JSON for /api/v1/profiles")
        sys.exit(1)

    if filter_tag:
        profiles = [
            p for p in profiles if filter_tag.lower() in [t.lower() for t in p.get("tags", [])]
        ]
        if not profiles:
            if quiet:
                click.echo("[]")
            else:
                console.print(f"[yellow]No profiles matched tag:[/] {filter_tag}")
            return

    if quiet:
        click.echo(json.dumps(profiles, indent=2))
        return

    _print_profiles_table(profiles, filter_tag)
    console.print(
        f"\n  [dim]{len(profiles)} profile(s) shown. "
        f"Run [bold]envforage fix --profile <slug>[/] to generate a setup script.[/]"
    )


def _print_profiles_table(profiles: list, filter_tag: str | None) -> None:
    table = Table(box=box.ROUNDED, show_header=True, padding=(0, 1), expand=False)
    table.add_column("Slug", style="bold cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Tags", style="dim")
    table.add_column("Description")

    for profile in profiles:
        if isinstance(profile, dict):
            slug = profile.get("slug", "N/A")
            name = profile.get("name", "Unknown")
            tags = ", ".join(profile.get("tags", []))
            desc = profile.get("description", "")
            table.add_row(slug, name, tags, desc)

    console.print(table)
