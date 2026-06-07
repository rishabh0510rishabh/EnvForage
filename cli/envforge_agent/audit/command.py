"""Click subcommand: `envforge audit <source-a> <source-b>`."""
from __future__ import annotations
from pathlib import Path
import sys

import click
from rich.console import Console

from .differ import diff
from .formatters import format_json, format_sarif, format_text
from .sources import ConfigFileSource ,LocalEnvironment, LockfileSource, Source


console = Console()
err_console = Console(stderr=True, style="bold red")


def _resolve_source(spec: str) -> Source:
    """Convert a CLI source string into a Source instance.

    Accepted forms:
        "local"                  -> the active Python environment
        path to .toml file       -> ConfigFileSource (Poetry pyproject.toml)
        path to any other file   -> LockfileSource (requirements.txt format)
    """
    if spec == "local":
        return LocalEnvironment()

    path = Path(spec)
    if path.exists() and path.is_file():
        if path.suffix.lower() == ".toml":
            return ConfigFileSource(path)
        return LockfileSource(path)

    raise click.BadParameter(
        f"Could not interpret source '{spec}'. "
        f"Use 'local', a path to a lockfile, or a path to a pyproject.toml."
    )


@click.command("audit")
@click.argument("source_a")
@click.argument("source_b")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit results as JSON to stdout instead of a Rich table.",
)
@click.option(
    "--sarif",
    "as_sarif",
    is_flag=True,
    help="Emit results as SARIF v2.1.0 to stdout (for CI/security tooling).",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Exit with code 1 if any drift is detected. For CI gating.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress all logging and standard output.",
)
def audit_command(source_a: str, source_b: str, as_json: bool, as_sarif: bool, strict: bool, quiet: bool) -> None:
    """Compare two environments and report drift.

    SOURCE_A and SOURCE_B can each be either:

    \b
        local                 the active Python environment (via pip list)
        path/to/lockfile.txt  a requirements.txt-style lockfile

    Examples:

    \b
        envforge audit local requirements.txt
        envforge audit requirements.lock requirements.txt
    """
    try:
        src_a = _resolve_source(source_a)
        src_b = _resolve_source(source_b)
    except click.BadParameter as exc:
        err_console.print(f"[ERROR] {exc.message}")
        sys.exit(2)

    try:
        result = diff(src_a, src_b)
    except RuntimeError as exc:
        err_console.print(f"[ERROR] {exc}")
        sys.exit(1)
    if as_json and as_sarif:
        err_console.print("[ERROR] --json and --sarif are mutually exclusive.")
        sys.exit(2)

    if as_json:
        click.echo(format_json(result))
    elif as_sarif:
        click.echo(format_sarif(result))
    elif not quiet:
        format_text(result, console)
    
    if strict and result.has_drift():
        sys.exit(1)