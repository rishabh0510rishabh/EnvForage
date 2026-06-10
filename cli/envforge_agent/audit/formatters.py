"""
Output formatters for envforge audit.

MVP includes only the text formatter (Rich-styled console output).
JSON and SARIF formatters will be added in follow-up PRs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
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
    "major": 0,
    "minor": 1,
    "patch": 2,
    "added": 3,
    "removed": 4,
    "other": 5,
}


def format_text(result: AuditResult, console: Console) -> None:
    """Print the audit result as a Rich-styled table on the given console."""
    console.print(f"\n[bold]Audit:[/] {result.source_a} -> {result.source_b}\n")

    if not result.has_drift():
        console.print(f"[bold green]No drift detected[/] ({result.common_count} packages match)")
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

    counts: dict[str, int] = {}
    for entry in result.differences:
        counts[entry.severity] = counts.get(entry.severity, 0) + 1

    summary = ", ".join(
        f"{counts[sev]} {sev}" for sev in sorted(counts, key=lambda s: SEVERITY_ORDER.get(s, 99))
    )
    console.print(
        f"\n[bold]Summary:[/] {len(result.differences)} differences "
        f"({summary}); {result.common_count} matching packages."
    )
    console.print(f"[bold]Drift score:[/] {result.drift_score}")


# Mapping from envforge severity to SARIF level
# SARIF levels: error, warning, note, none
SEVERITY_TO_SARIF_LEVEL = {
    "major": "error",
    "minor": "warning",
    "patch": "note",
    "added": "warning",
    "removed": "warning",
    "other": "note",
}


def format_json(result: AuditResult) -> str:
    """Render an AuditResult as a stable JSON document.

    The schema is intentionally flat and machine-friendly for downstream tools
    (CI checks, dashboards, custom diff viewers).
    """
    counts: dict[str, int] = {}
    for entry in result.differences:
        counts[entry.severity] = counts.get(entry.severity, 0) + 1

    payload = {
        "source_a": result.source_a,
        "source_b": result.source_b,
        "differences": [
            {
                "package": entry.package,
                "version_a": entry.a_version,
                "version_b": entry.b_version,
                "severity": entry.severity,
            }
            for entry in result.differences
        ],
        "summary": {
            "total": len(result.differences),
            "by_severity": counts,
            "common_count": result.common_count,
            "drift_score": result.drift_score,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=False)


def format_sarif(result: AuditResult) -> str:
    """Render an AuditResult as SARIF v2.1.0.

    SARIF (Static Analysis Results Interchange Format) is consumable by
    GitHub Advanced Security, Azure DevOps, and other static-analysis
    aggregators. Each drift entry is a SARIF result; severity maps to
    SARIF level.
    """
    # Unique rules — one per severity that actually appears
    severities_present = sorted({entry.severity for entry in result.differences})
    rules = [
        {
            "id": f"drift-{sev}",
            "name": f"Drift{sev.capitalize()}",
            "shortDescription": {"text": f"{sev.capitalize()} version drift"},
            "defaultConfiguration": {"level": SEVERITY_TO_SARIF_LEVEL.get(sev, "note")},
        }
        for sev in severities_present
    ]

    results = [
        {
            "ruleId": f"drift-{entry.severity}",
            "level": SEVERITY_TO_SARIF_LEVEL.get(entry.severity, "note"),
            "message": {
                "text": (
                    f"{entry.package}: "
                    f"{entry.a_version or '(absent)'} -> "
                    f"{entry.b_version or '(absent)'} "
                    f"({entry.severity})"
                )
            },
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": result.source_b}}}],
            "properties": {
                "package": entry.package,
                "versionA": entry.a_version,
                "versionB": entry.b_version,
                "sourceA": result.source_a,
                "sourceB": result.source_b,
            },
        }
        for entry in result.differences
    ]

    sarif = {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "envforge-audit",
                        "informationUri": "https://github.com/rishabh0510rishabh/EnvForage",
                        "rules": rules,
                    }
                },
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "endTimeUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }
                ],
                "results": results,
                "properties": {
                    "driftScore": result.drift_score,
                    "totalDifferences": len(result.differences),
                    "commonCount": result.common_count,
                },
            }
        ],
    }
    return json.dumps(sarif, indent=2, sort_keys=False)
