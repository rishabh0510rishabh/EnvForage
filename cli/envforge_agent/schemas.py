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
    version: str | None = None       # e.g. "5.6"
    gcn_arch: str | None = None      # e.g. "gfx1030"


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
    agent_version: str = Field("1.0.1", description="envforge-agent version")
    os: OSInfo
    cpu: CPUInfo
    ram: RAMInfo
    gpus: list[GPUInfo] = Field(default_factory=list)
    cuda: CUDAInfo = Field(default_factory=CUDAInfo)
    rocm: ROCMInfo = Field(default_factory=ROCMInfo)
    python_installations: list[PythonInfo] = Field(default_factory=list)
    active_python: PythonInfo | None = None

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string (API-compatible)."""
        return self.model_dump_json(indent=indent)

    def to_sarif(self) -> dict:
        """Serialize diagnostic report to SARIF 2.1.0 format for CI/CD pipelines."""
        results = []

        # GPU check
        if not self.gpus:
            results.append({
                "ruleId": "ENV001",
                "level": "warning",
                "message": {"text": "No NVIDIA GPU detected on this system."},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": "system/gpu"}}}],
            })

        # CUDA check
        if not self.cuda.version:
            results.append({
                "ruleId": "ENV002",
                "level": "warning",
                "message": {"text": "CUDA is not detected on this system."},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": "system/cuda"}}}],
            })

        # Python check
        if not self.active_python:
            results.append({
                "ruleId": "ENV003",
                "level": "error",
                "message": {"text": "No active Python installation detected."},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": "system/python"}}}],
            })

        return {
            "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "envforge-agent",
                            "version": self.agent_version,
                            "rules": [
                                {"id": "ENV001", "name": "NoGPU", "shortDescription": {"text": "No GPU detected"}},
                                {"id": "ENV002", "name": "NoCUDA", "shortDescription": {"text": "CUDA not detected"}},
                                {"id": "ENV003", "name": "NoPython", "shortDescription": {"text": "No Python detected"}},
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
                    },
                }
            ],
        }