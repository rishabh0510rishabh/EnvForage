"""Pydantic schemas for the analytics summary endpoint."""

from pydantic import BaseModel, Field


class AnalyticsSummaryResponse(BaseModel):
    gpu_distribution: dict[str, int] = Field(
        ..., description="Report count by GPU vendor: NVIDIA, AMD, Intel, No GPU."
    )
    python_version_histogram: dict[str, int] = Field(
        ..., description="Report count per Python version (major.minor)."
    )
    cuda_version_heatmap: list[dict[str, str | int]] = Field(
        ..., description="Matrix rows: {cuda_version, gpu_name, count}."
    )
    os_distribution: dict[str, int] = Field(..., description="Report count per OS type.")
    common_failures: dict[str, int] = Field(
        ..., description="Top 10 most common compatibility check failures."
    )
