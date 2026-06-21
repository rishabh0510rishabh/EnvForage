"""Data types for envforage audit."""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional


def _normalize_name(name: str) -> str:
    """PEP 503 normalization: lowercase, collapse runs of _-. to single hyphen."""
    return re.sub(r"[-_.]+", "-", name).lower()


# Weighted contribution of each severity to the overall drift score.
# Major changes count heavily (semver-breaking); patch changes minimally.
SEVERITY_WEIGHTS = {
    "major": 10,
    "minor": 3,
    "patch": 1,
    "added": 2,
    "removed": 2,
    "other": 1,
}


@dataclass(frozen=True)
class Package:
    """Resolved package entry: name (normalized per PEP 503) + version string.

    Normalization ensures `Pillow` and `pillow` compare as the same package,
    and `pytest-asyncio` and `pytest_asyncio` are also unified.
    """

    name: str
    version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _normalize_name(self.name))


@dataclass
class DiffEntry:
    """A single difference between two sources for one package.

    severity is one of: "added", "removed", "major", "minor", "patch", "other".
    "added" means the package is only in source B; "removed" only in source A.
    """

    package: str
    a_version: Optional[str]
    b_version: Optional[str]
    severity: str


@dataclass
class AuditResult:
    """Outcome of comparing two sources."""

    source_a: str
    source_b: str
    differences: List[DiffEntry] = field(default_factory=list)
    common_count: int = 0

    def has_drift(self) -> bool:
        return len(self.differences) > 0

    @property
    def drift_score(self) -> int:
        """Weighted single-number drift indicator (0 = perfect match).

        Heavier weight for breaking changes (major) so a single major drift
        ranks higher than several patch drifts. Useful as a CI threshold.
        """
        return sum(SEVERITY_WEIGHTS.get(d.severity, 1) for d in self.differences)
