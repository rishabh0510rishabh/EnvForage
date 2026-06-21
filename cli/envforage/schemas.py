"""
Pydantic data models for the DiagnosticReport.

These models are kept in sync with the backend's:
  backend/app/schemas/diagnostic.py

The CLI agent uses these models to validate its own output before
writing to stdout or sending to the API.

IMPORTANT: The JSON output of these models IS the API request body for
POST /api/v1/diagnose. Any field change here requires a corresponding
change in the backend schema.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from envforage import __version__


class OSInfo(BaseModel):
    name: str
    version: str
    architecture: str
    wsl_version: str | None = None


class CPUInfo(BaseModel):
    brand: str
    cores: int
    threads: int


class RAMInfo(BaseModel):
    total_gb: float
    available_gb: float


class GPUInfo(BaseModel):
    name: str
    vram_gb: float | None = None
    driver_version: str | None = None
    index: int = 0


class CUDAInfo(BaseModel):
    version: str | None = None
    toolkit_path: str | None = None
    cudnn_version: str | None = None
    nccl_version: str | None = None


class ROCMInfo(BaseModel):
    version: str | None = None  # e.g. "5.6"
    gcn_arch: str | None = None  # e.g. "gfx1030"


class DISKInfo(BaseModel):
    total_gb: float = 0.0
    available_gb: float = 0.0


class PythonInfo(BaseModel):
    version: str
    path: str
    is_venv: bool = False
    venv_path: str | None = None
    pip_version: str | None = None


class DiagnosticReport(BaseModel):
    """
    Structured diagnostic report produced by the CLI agent.

    This is both the CLI output format and the POST /api/v1/diagnose request body.
    Fields must remain in sync with backend/app/schemas/diagnostic.py.
    """

    agent_version: str = Field(default=__version__, description="envforage version")
    os: OSInfo
    cpu: CPUInfo
    ram: RAMInfo
    gpus: list[GPUInfo] = Field(default_factory=list)
    cuda: CUDAInfo = Field(default_factory=CUDAInfo)
    rocm: ROCMInfo = Field(default_factory=ROCMInfo)
    disk: DISKInfo = Field(default_factory=DISKInfo)
    python_installations: list[PythonInfo] = Field(default_factory=list)
    active_python: PythonInfo | None = None

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string (API-compatible)."""
        return self.model_dump_json(indent=indent)

    def to_markdown(self) -> str:
        """Serialize diagnostic report to a Markdown-formatted string."""
        lines = ["# EnvForage Diagnostic Report", ""]

        lines += [
            "## System",
            f"- **OS**: {self.os.name} {self.os.version} ({self.os.architecture})",
        ]
        if self.os.wsl_version:
            lines.append(f"- **WSL**: {self.os.wsl_version}")
        lines += [
            f"- **CPU**: {self.cpu.brand} — {self.cpu.cores}C / {self.cpu.threads}T",
            f"- **RAM**: {self.ram.total_gb} GB total, {self.ram.available_gb} GB free",
            f"- **Disk**: {self.disk.available_gb:.1f} GB free of {self.disk.total_gb:.1f} GB",
            "",
        ]

        lines.append("## GPU")
        if self.gpus:
            for gpu in self.gpus:
                vram = f"{gpu.vram_gb} GB" if gpu.vram_gb else "?"
                driver = gpu.driver_version or "?"
                lines.append(f"- **{gpu.name}**: {vram} VRAM, driver {driver}")
        else:
            lines.append("- No NVIDIA GPU detected")
        lines.append("")

        lines.append("## CUDA")
        if self.cuda.version:
            lines.append(f"- **Version**: {self.cuda.version}")
            if self.cuda.cudnn_version:
                lines.append(f"- **cuDNN**: {self.cuda.cudnn_version}")
            if self.cuda.nccl_version:
                lines.append(f"- **NCCL**: {self.cuda.nccl_version}")
            if self.cuda.toolkit_path:
                lines.append(f"- **Toolkit Path**: {self.cuda.toolkit_path}")
        else:
            lines.append("- Not detected")
        lines.append("")

        lines.append("## ROCm")
        if self.rocm.version:
            gcn = f" (GCN {self.rocm.gcn_arch})" if self.rocm.gcn_arch else ""
            lines.append(f"- **Version**: {self.rocm.version}{gcn}")
        else:
            lines.append("- Not detected")
        lines.append("")

        lines.append("## Python")
        if self.active_python:
            py = self.active_python
            venv = " (venv)" if py.is_venv else ""
            lines.append(f"- **Active**: {py.version} at `{py.path}`{venv}")
        if len(self.python_installations) >= 1:
            others = [
                p
                for p in self.python_installations
                if p.path != (self.active_python.path if self.active_python else "")
            ]
            if others:
                lines.append(
                    "- **Others**: " + ", ".join(f"{p.version} (`{p.path}`)" for p in others[:3])
                )
        lines.append("")

        return "\n".join(lines)

    def to_sarif(self) -> dict:
        """Serialize diagnostic report to SARIF 2.1.0 format for CI/CD pipelines."""
        results = []

        # GPU check
        if not self.gpus:
            results.append(
                {
                    "ruleId": "ENV001",
                    "level": "warning",
                    "message": {"text": "No NVIDIA GPU detected on this system."},
                    "locations": [
                        {"physicalLocation": {"artifactLocation": {"uri": "system/gpu"}}}
                    ],
                }
            )

        # CUDA check
        if not self.cuda.version:
            results.append(
                {
                    "ruleId": "ENV002",
                    "level": "warning",
                    "message": {"text": "CUDA is not detected on this system."},
                    "locations": [
                        {"physicalLocation": {"artifactLocation": {"uri": "system/cuda"}}}
                    ],
                }
            )

        # Python check
        if not self.active_python:
            results.append(
                {
                    "ruleId": "ENV003",
                    "level": "error",
                    "message": {"text": "No active Python installation detected."},
                    "locations": [
                        {"physicalLocation": {"artifactLocation": {"uri": "system/python"}}}
                    ],
                }
            )

        return {
            "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "envforage",
                            "version": self.agent_version,
                            "rules": [
                                {
                                    "id": "ENV001",
                                    "name": "NoGPU",
                                    "shortDescription": {"text": "No GPU detected"},
                                },
                                {
                                    "id": "ENV002",
                                    "name": "NoCUDA",
                                    "shortDescription": {"text": "CUDA not detected"},
                                },
                                {
                                    "id": "ENV003",
                                    "name": "NoPython",
                                    "shortDescription": {"text": "No Python detected"},
                                },
                            ],
                        }
                    },
                    "results": results,
                    "properties": {
                        "os": f"{self.os.name} {self.os.version}",
                        "cpu": self.cpu.brand,
                        "ram_gb": self.ram.total_gb,
                        "python": self.active_python.version if self.active_python else None,
                        "cuda": self.cuda.version,
                        "disk": self.disk.total_gb,
                    },
                }
            ],
        }
