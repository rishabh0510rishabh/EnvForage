"""
Output formatters for envforge audit.

MVP includes only the text formatter (Rich-styled console output).
JSON and SARIF formatters will be added in follow-up PRs.
"""
from __future__ import annotations
from rich.console import Console
from rich.table import Table
from rich import box

from .models import AuditResult


SEVERITY_STYLES = {
    "major": "bold red",
    "minor": "yellow",
    "patch": "green",
    "added": "cyan",
    "removed": "magenta",
    "other": "white",
}

SEVERITY_ORDER = {
    "major": 0, "minor": 1, "patch": 2, "added": 3, "removed": 4, "other": 5,
}


def format_text(result: AuditResult, console: Console) -> None:
    """Print the audit result as a Rich-styled table on the given console."""
    console.print(
        f"\n[bold]Audit:[/] {result.source_a} -> {result.source_b}\n"
    )

    if not result.has_drift():
        console.print(
            f"[bold green]No drift detected[/] "
            f"({result.common_count} packages match)"
        )
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("Package")
    table.add_column(result.source_a, justify="left")
    table.add_column(result.source_b, justify="left")
    table.add_column("Severity")

    sorted_diffs = sorted(
        result.differences,
        key=lambda d: (SEVERITY_ORDER.get(d.severity, 99), d.package),
    )

    for entry in sorted_diffs:
        style = SEVERITY_STYLES.get(entry.severity, "white")
        table.add_row(
            entry.package,
            entry.a_version or "-",
            entry.b_version or "-",
            f"[{style}]{entry.severity}[/]",
        )

    console.print(table)

    counts = {}
    for entry in result.differences:
        counts[entry.severity] = counts.get(entry.severity, 0) + 1

    summary = ", ".join(
        f"{counts[sev]} {sev}"
        for sev in sorted(counts, key=lambda s: SEVERITY_ORDER.get(s, 99))
    )
    console.print(
        f"\n[bold]Summary:[/] {len(result.differences)} differences "
        f"({summary}); {result.common_count} matching packages."
    )