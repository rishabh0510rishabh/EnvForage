"""Click subcommand: `envforge audit <source-a> <source-b>`."""
from __future__ import annotations
from pathlib import Path
import sys

import click
from rich.console import Console

from .differ import diff
from .formatters import format_text
from .sources import LocalEnvironment, LockfileSource, Source


console = Console()
err_console = Console(stderr=True, style="bold red")


def _resolve_source(spec: str) -> Source:
    """Convert a CLI source string into a Source instance.

    Accepted forms:
        "local"             -> the active Python environment
        path to a file      -> LockfileSource (must exist on disk)
    """
    if spec == "local":
        return LocalEnvironment()

    path = Path(spec)
    if path.exists() and path.is_file():
        return LockfileSource(path)

    raise click.BadParameter(
        f"Could not interpret source '{spec}'. "
        f"Use 'local' or a path to a lockfile."
    )


@click.command("audit")
@click.argument("source_a", required=True)
@click.argument("source_b", required=True)
def audit_command(source_a: str, source_b: str) -> None:
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

    format_text(result, console)