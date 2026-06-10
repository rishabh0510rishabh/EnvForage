"""Pydantic schemas for compatibility matrix admin CRUD operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CUDAMatrixCreate(BaseModel):
    cuda_version: str = Field(
        ..., description="CUDA version, e.g. 12.1", min_length=2, max_length=16
    )
    min_driver_linux: str = Field(
        ..., description="Minimum Linux driver version", max_length=32
    )
    min_driver_windows: str = Field(
        ..., description="Minimum Windows driver version", max_length=32
    )
    cudnn_versions: list[str] = Field(..., description="Supported cuDNN versions")
    supported_archs: list[str] = Field(
        ..., description="Supported GPU architectures (sm_xx)"
    )
    notes: str | None = Field(None, description="Notes")
    source_url: str | None = Field(None, description="Source URL documentation")


class CUDAMatrixUpdate(BaseModel):
    min_driver_linux: str | None = Field(None, max_length=32)
    min_driver_windows: str | None = Field(None, max_length=32)
    cudnn_versions: list[str] | None = None
    supported_archs: list[str] | None = None
    notes: str | None = None
    source_url: str | None = None


class CUDAMatrixResponse(CUDAMatrixCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class RocmMatrixCreate(BaseModel):
    rocm_version: str = Field(
        ..., description="ROCm version, e.g. 6.0.0", min_length=2, max_length=16
    )
    min_driver_linux: str = Field(
        ..., description="Minimum Linux driver version", max_length=32
    )
    supported_gpus: list[str] = Field(
        ..., description="Supported GPU architectures (gfx_xxx)"
    )
    notes: str | None = Field(None, description="Notes")
    source_url: str | None = Field(None, description="Source URL")


class RocmMatrixUpdate(BaseModel):
    min_driver_linux: str | None = Field(None, max_length=32)
    supported_gpus: list[str] | None = None
    notes: str | None = None
    source_url: str | None = None


class RocmMatrixResponse(RocmMatrixCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class PythonMatrixCreate(BaseModel):
    framework: str = Field(..., description="Framework name, e.g. torch", max_length=64)
    version: str = Field(
        ..., description="Framework version, e.g. 2.1.0", max_length=64
    )
    min_python: str = Field(
        ..., description="Minimum Python version, e.g. 3.8", max_length=16
    )
    max_python: str = Field(
        ..., description="Maximum Python version, e.g. 3.11", max_length=16
    )
    supported_cuda: list[str] = Field(
        default_factory=list, description="Supported CUDA versions"
    )
    supported_rocm: list[str] = Field(
        default_factory=list, description="Supported ROCm versions"
    )
    supported_python: list[str] = Field(
        default_factory=list, description="Supported Python versions list"
    )


class PythonMatrixUpdate(BaseModel):
    min_python: str | None = Field(None, max_length=16)
    max_python: str | None = Field(None, max_length=16)
    supported_cuda: list[str] | None = None
    supported_rocm: list[str] | None = None
    supported_python: list[str] | None = None


class PythonMatrixResponse(PythonMatrixCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
