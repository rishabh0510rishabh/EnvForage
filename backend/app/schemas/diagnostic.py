"""Pydantic schemas for diagnostic reports."""

from pydantic import BaseModel, Field


class OSInfo(BaseModel):
    name: str = Field(
        ...,
        max_length=128,
        description="Operating system name.",
        examples=["Ubuntu 22.04"],
    )
    version: str = Field(
        ...,
        max_length=32,
        description="Operating system version.",
        examples=["22.04"],
    )
    architecture: str = Field(
        ...,
        max_length=32,
        description="CPU architecture of the operating system.",
        examples=["x86_64"],
    )
    wsl_version: str | None = Field(
        None,
        description="WSL version if running inside Windows Subsystem for Linux.",
        examples=["WSL2"],
    )


class CPUInfo(BaseModel):
    brand: str = Field(
        ...,
        max_length=256,
        description="CPU model or brand name.",
        examples=["AMD Ryzen 7 7840HS"],
    )
    cores: int = Field(
        ...,
        description="Number of physical CPU cores.",
        examples=[8],
    )
    threads: int = Field(
        ...,
        description="Number of CPU threads.",
        examples=[16],
    )


class RAMInfo(BaseModel):
    total_gb: float = Field(
        ...,
        description="Total installed RAM in GB.",
        examples=[16.0],
    )
    available_gb: float = Field(
        ...,
        description="Currently available RAM in GB.",
        examples=[10.5],
    )


class GPUInfo(BaseModel):
    name: str = Field(
        ...,
        max_length=128,
        description="GPU model name.",
        examples=["NVIDIA RTX 4060 Laptop GPU"],
    )
    vram_gb: float | None = Field(
        None,
        description="Available GPU VRAM in GB.",
        examples=[8.0],
    )
    driver_version: str | None = Field(
        None,
        max_length=32,
        description="Installed GPU driver version.",
        examples=["555.85"],
    )
    index: int = Field(
        0,
        description="GPU index in multi-GPU systems.",
        examples=[0],
    )


class CUDAInfo(BaseModel):
    version: str | None = Field(
        None,
        description="Installed CUDA version.",
        examples=["12.1"],
    )
    toolkit_path: str | None = Field(
        None,
        description="Filesystem path to the CUDA toolkit.",
        examples=["/usr/local/cuda"],
    )
    cudnn_version: str | None = Field(
        None,
        description="Installed cuDNN version.",
        examples=["8.9"],
    )
    nccl_version: str | None = Field(
        None,
        description="Installed NCCL version.",
        examples=["2.18"],
    )


class ROCMInfo(BaseModel):
    version: str | None = Field(
        None,
        description="Installed ROCm version.",
        examples=["5.6"],
    )
    gcn_arch: str | None = Field(
        None,
        description="AMD GPU architecture identifier.",
        examples=["gfx1030"],
    )


class PythonInfo(BaseModel):
    version: str = Field(
        ...,
        max_length=8,
        description="Installed Python version.",
        examples=["3.11.4"],
    )
    path: str = Field(
        ...,
        max_length=512,
        description="Filesystem path to the Python executable.",
        examples=["/usr/bin/python3"],
    )
    is_venv: bool = Field(
        False,
        description="Whether the Python installation is a virtual environment.",
        examples=[True],
    )
    venv_path: str | None = Field(
        None,
        description="Path to the Python virtual environment.",
        examples=["/home/user/project/.venv"],
    )
    pip_version: str | None = Field(
        None,
        description="Installed pip version.",
        examples=["24.0"],
    )


class DiagnosticReportSchema(BaseModel):
    """
    Structured diagnostic report produced by the CLI agent.
    This is both the CLI output format and the POST /diagnose request body.
    """

    agent_version: str = Field(
        "1.0.0",
        description="Version of the envforge-agent CLI.",
        examples=["1.0.0"],
    )
    os: OSInfo
    cpu: CPUInfo
    ram: RAMInfo
    gpus: list[GPUInfo] = Field(
        default_factory=list,
        max_length=32,
        description="Detected GPUs on the system. Capped at 32 entries to prevent memory exhaustion.",
    )
    cuda: CUDAInfo = Field(
        default_factory=lambda: CUDAInfo(
            version=None,
            toolkit_path=None,
            cudnn_version=None,
            nccl_version=None,
        ),
        description="Detected CUDA installation information.",
    )

    rocm: ROCMInfo = Field(
        default_factory=lambda: ROCMInfo(
            version=None,
            gcn_arch=None,
        ),
        description="Detected ROCm installation information.",
    )
    python_installations: list[PythonInfo] = Field(
        default_factory=list,
        max_length=64,
        description="All detected Python installations. Capped at 64 entries to prevent memory exhaustion.",
    )
    active_python: PythonInfo | None = Field(
        None,
        description="Currently active Python interpreter.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "agent_version": "1.0.0",
                "os": {
                    "name": "Ubuntu 22.04",
                    "version": "22.04",
                    "architecture": "x86_64",
                    "wsl_version": None,
                },
                "cpu": {
                    "brand": "AMD Ryzen 7 7840HS",
                    "cores": 8,
                    "threads": 16,
                },
                "ram": {
                    "total_gb": 16.0,
                    "available_gb": 10.5,
                },
                "gpus": [
                    {
                        "name": "NVIDIA RTX 4060 Laptop GPU",
                        "vram_gb": 8.0,
                        "driver_version": "555.85",
                        "index": 0,
                    }
                ],
                "cuda": {
                    "version": "12.1",
                    "toolkit_path": "/usr/local/cuda",
                    "cudnn_version": "8.9",
                    "nccl_version": "2.18",
                },
                "rocm": {
                    "version": None,
                    "gcn_arch": None,
                },
                "python_installations": [
                    {
                        "version": "3.11.4",
                        "path": "/usr/bin/python3",
                        "is_venv": True,
                        "venv_path": "/home/user/project/.venv",
                        "pip_version": "24.0",
                    }
                ],
                "active_python": {
                    "version": "3.11.4",
                    "path": "/usr/bin/python3",
                    "is_venv": True,
                    "venv_path": "/home/user/project/.venv",
                    "pip_version": "24.0",
                },
            }
        }
    }


class CompatibilityIssue(BaseModel):
    severity: str = Field(
        ...,
        description="Issue severity level.",
        examples=["ERROR"],
    )
    component: str = Field(
        ...,
        description="System component related to the issue.",
        examples=["cuda"],
    )
    message: str = Field(
        ...,
        description="Human-readable explanation of the issue.",
        examples=["CUDA version is incompatible with installed driver."],
    )
    suggested_fix: str | None = Field(
        None,
        description="Suggested fix or remediation step.",
        examples=["Upgrade the NVIDIA driver to version 555 or later."],
    )
    docs_url: str | None = Field(
        None,
        description="Optional documentation URL for troubleshooting.",
        examples=["https://docs.nvidia.com/cuda/"],
    )


class DiagnoseResponse(BaseModel):
    """Response for POST /diagnose."""

    report_id: str = Field(
        ...,
        description="Unique identifier for the stored diagnostic report.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    compatible_profiles: list[str] = Field(
        ...,
        description="Profiles compatible with the detected system.",
        examples=[["pytorch-cu121"]],
    )
    issues: list[CompatibilityIssue] = Field(
        ...,
        description="Detected compatibility issues.",
    )
    recommendations: list[str] = Field(
        ...,
        description="General compatibility recommendations.",
        examples=[["Upgrade NVIDIA driver to latest stable release"]],
    )


class TaskResponse(BaseModel):
    """Response when a task is offloaded to Celery."""
    task_id: str = Field(..., description="Celery task ID for polling.")
    status: str = Field(..., description="Current status of the task.")


class DiagnoseTaskStatus(BaseModel):
    """Response for GET /diagnose/status/{task_id}."""
    task_id: str
    status: str
    result: DiagnoseResponse | None = None
    error: str | None = None
