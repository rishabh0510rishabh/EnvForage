"""Pydantic schemas for diagnostic reports."""

from pydantic import BaseModel, Field


class OSInfo(BaseModel):
    name: str                        # e.g. "Windows 11", "Ubuntu 22.04"
    version: str
    architecture: str                # e.g. "x86_64"
    wsl_version: str | None = None   # e.g. "WSL2"


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
    version: str | None = None       # e.g. "12.1"
    toolkit_path: str | None = None
    cudnn_version: str | None = None
    nccl_version: str | None = None


class ROCMInfo(BaseModel):
    version: str | None = None       # e.g. "5.6"
    gcn_arch: str | None = None      # e.g. "gfx1030"


class PythonInfo(BaseModel):
    version: str                     # e.g. "3.11.4"
    path: str
    is_venv: bool = False
    venv_path: str | None = None
    pip_version: str | None = None


class DiagnosticReportSchema(BaseModel):
    """
    Structured diagnostic report produced by the CLI agent.
    This is both the CLI output format and the POST /diagnose request body.
    """
    agent_version: str = Field("1.0.0", description="envforge-agent version")
    os: OSInfo
    cpu: CPUInfo
    ram: RAMInfo
    gpus: list[GPUInfo] = Field(default_factory=list)
    cuda: CUDAInfo = Field(default_factory=CUDAInfo)
    rocm: ROCMInfo = Field(default_factory=ROCMInfo)
    python_installations: list[PythonInfo] = Field(default_factory=list)
    active_python: PythonInfo | None = None


class CompatibilityIssue(BaseModel):
    severity: str                    # "ERROR" | "WARNING" | "INFO"
    component: str                   # "cuda" | "driver" | "python"
    message: str
    suggested_fix: str | None = None
    docs_url: str | None = None


class DiagnoseResponse(BaseModel):
    """Response for POST /diagnose."""
    report_id: str
    compatible_profiles: list[str]
    issues: list[CompatibilityIssue]
    recommendations: list[str]
