"""
Diff algorithm for envforge audit.

Compares two Source instances and produces an AuditResult. Severity is
classified using a semver-style heuristic; the existing compatibility engine
will be wired in as a follow-up to refine which deltas are likely breaking.
"""

from __future__ import annotations
from typing import Dict
from packaging.version import InvalidVersion, parse as parse_version

from .models import AuditResult, DiffEntry
from .sources import Source


def _classify_version_change(a: str | None, b: str | None) -> str:
    """Classify a version change by semver-style severity.

    Returns one of: "major", "minor", "patch", "other".
    Non-numeric or unparseable version strings fall through to "other".
    """
    try:
        a_ver = parse_version(a) if a is not None else None
        b_ver = parse_version(b) if b is not None else None
    except (InvalidVersion, TypeError):
        return "other"

    if a_ver is None or b_ver is None:
        return "other"

    if a_ver == b_ver:
        return "other"

    if a_ver.major != b_ver.major:
        return "major"
    if a_ver.minor != b_ver.minor:
        return "minor"

    # If major and minor are identical, and they are not equal, then
    # it's a patch or pre-release/post-release/dev/local change (patch level).
    return "patch"


def _to_dict(source: Source) -> Dict[str, str]:
    return {p.name: p.version for p in source.packages()}


def diff(source_a: Source, source_b: Source) -> AuditResult:
    """Compare two sources; return an AuditResult listing every difference."""
    a_packages = _to_dict(source_a)
    b_packages = _to_dict(source_b)

    all_names = sorted(set(a_packages) | set(b_packages))

    differences = []
    common_count = 0

    for name in all_names:
        a_ver = a_packages.get(name)
        b_ver = b_packages.get(name)

        if a_ver is None:
            differences.append(
                DiffEntry(package=name, a_version=None, b_version=b_ver, severity="added")
            )
        elif b_ver is None:
            differences.append(
                DiffEntry(package=name, a_version=a_ver, b_version=None, severity="removed")
            )
        elif a_ver == b_ver:
            common_count += 1
        else:
            differences.append(
                DiffEntry(
                    package=name,
                    a_version=a_ver,
                    b_version=b_ver,
                    severity=_classify_version_change(a_ver, b_ver),
                )
            )

    return AuditResult(
        source_a=source_a.name,
        source_b=source_b.name,
        differences=differences,
        common_count=common_count,
    )
