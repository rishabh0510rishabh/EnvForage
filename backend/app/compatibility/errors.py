"""
Compatibility Engine error types.

All errors are structured with actionable context — no bare string exceptions.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IncompatibilityError(Exception):
    """
    Raised when a set of constraints cannot be resolved to a compatible
    environment. Always carries enough context to display a useful error message.
    """
    component: str         # e.g. "cuda", "torch", "python"
    constraint: str        # What was required, e.g. "CUDA >= 11.8"
    detected: str          # What was found / requested, e.g. "CUDA 11.6"
    suggestion: str        # Human-readable fix hint
    docs_url: str = ""     # Official docs link if available

    def __str__(self) -> str:
        return (
            f"[{self.component.upper()}] {self.constraint} "
            f"(found: {self.detected}). "
            f"Fix: {self.suggestion}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": "INCOMPATIBLE_VERSIONS",
            "component": self.component,
            "constraint": self.constraint,
            "detected": self.detected,
            "suggestion": self.suggestion,
            "docs_url": self.docs_url,
        }


@dataclass
class UnknownVersionError(Exception):
    """Raised when a requested version is not in the compatibility matrix."""
    component: str
    version: str
    known_versions: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        known = ", ".join(self.known_versions) if self.known_versions else "none"
        return (
            f"Unknown {self.component} version: {self.version}. "
            f"Known versions: {known}"
        )


@dataclass
class UnsupportedOSError(Exception):
    """Raised when a profile does not support the requested OS."""
    profile_slug: str
    requested_os: str
    supported_os: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Profile '{self.profile_slug}' does not support OS '{self.requested_os}'. "
            f"Supported: {', '.join(self.supported_os)}"
        )
