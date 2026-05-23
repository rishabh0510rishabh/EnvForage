"""
Data models for the Compatibility Engine.
Pure dataclasses — no I/O, no database, no side effects.
"""
from dataclasses import dataclass, field
from typing import Any, Literal

OSTarget = Literal["LINUX", "WSL", "WIN"]


@dataclass(frozen=True)
class PackageConstraint:
    """A single package with its version specification."""
    name: str
    version_spec: str          # e.g. "2.1.0" or ">=2.0,<2.2"
    cuda_variant: str | None = None   # e.g. "cu118", None for CPU-only


@dataclass(frozen=True)
class ResolvedPackage:
    """A package with its fully resolved, pinned version."""
    name: str
    version: str               # Exact pinned version, e.g. "2.1.0"
    cuda_variant: str | None = None


@dataclass
class ResolvedEnvironment:
    """
    The output of CompatibilityResolver.resolve().
    Represents a fully validated, compatible environment configuration.
    """
    python_version: str                           # e.g. "3.11"
    cuda_version: str | None                      # e.g. "12.1", None for CPU
    target_os: OSTarget
    rocm_version: str | None = None               # e.g. "5.6", None for CPU/CUDA
    packages: list[ResolvedPackage] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "python_version": self.python_version,
            "cuda_version": self.cuda_version,
            "rocm_version": self.rocm_version,
            "target_os": self.target_os,
            "packages": [
                {
                    "name": p.name,
                    "version": p.version,
                    "cuda_variant": p.cuda_variant,
                }
                for p in self.packages
            ],
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class CUDAMatrixEntry:
    """
    Compatibility data for a specific CUDA version.
    Sourced from NVIDIA official documentation.
    """
    cuda_version: str
    min_driver_linux: str
    min_driver_windows: str
    cudnn_versions: list[str]
    supported_archs: list[str]
    notes: str = ""
    source_url: str = ""


@dataclass(frozen=True)
class ROCMMatrixEntry:
    """
    Compatibility data for a specific ROCm version.
    Sourced from AMD official documentation.
    """
    rocm_version: str
    min_driver_linux: str
    supported_gpus: list[str]
    notes: str = ""
    source_url: str = ""


@dataclass(frozen=True)
class FrameworkVersionEntry:
    """
    Python compatibility data for a specific framework version.
    """
    framework: str
    version: str
    min_python: str
    max_python: str
    supported_cuda: list[str] = field(default_factory=list)
    supported_rocm: list[str] = field(default_factory=list)
    supported_python: list[str] = field(default_factory=list)
