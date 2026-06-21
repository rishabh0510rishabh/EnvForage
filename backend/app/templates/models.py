"""Data models for the Template Engine."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.compatibility.models import ResolvedEnvironment


@dataclass
class TemplateContext:
    """
    Context object passed to all Jinja2 templates.
    Built from a validated ResolvedEnvironment + profile metadata.
    """

    profile_id: str
    profile_name: str
    resolved: ResolvedEnvironment
    envforage_version: str = "2.0.0"
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    warnings: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    use_uv: bool = False
    use_micromamba: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for Jinja2 rendering."""
        return {
            "profile": {
                "id": self.profile_id,
                "name": self.profile_name,
            },
            "python_version": self.resolved.python_version,
            "cuda_version": self.resolved.cuda_version,
            "rocm_version": self.resolved.rocm_version,
            "target_os": self.resolved.target_os,
            "packages": [
                {
                    "name": p.name,
                    "version": p.version,
                    "cuda_variant": p.cuda_variant,
                    # Build pip install string: e.g. "torch==2.1.0+cu118"
                    "pip_spec": (
                        f"{p.name}=={p.version}+{p.cuda_variant}"
                        if p.cuda_variant
                        else f"{p.name}=={p.version}"
                    ),
                }
                for p in self.resolved.packages
            ],
            "warnings": self.warnings,
            "generated_at": self.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
            "envforage_version": self.envforage_version,
            "use_uv": self.use_uv,
            "use_micromamba": self.use_micromamba,
            **self.extra,
        }


@dataclass
class RenderResult:
    """The output of a single template rendering operation."""

    filename: str
    content: str
    size_bytes: int = field(init=False)

    def __post_init__(self) -> None:
        self.size_bytes = len(self.content.encode("utf-8"))
