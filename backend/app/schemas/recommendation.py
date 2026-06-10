"""Pydantic schemas for the recommendation engine."""

from pydantic import BaseModel, Field


class RecommendedProfile(BaseModel):
    name: str = Field(
        ...,
        description="Profile slug identifier.",
        examples=["pytorch-cuda"],
    )
    reason: str = Field(
        ...,
        description="Why this profile is recommended for the detected hardware.",
        examples=["GPU with 8.0 GB VRAM — suitable for PyTorch CUDA workloads"],
    )
    rank: int = Field(
        ...,
        description="Rank order (1 = best match).",
        examples=[1],
    )


class RecommendationResponse(BaseModel):
    """Response for POST /api/v1/recommend."""

    recommended_profiles: list[RecommendedProfile] = Field(
        ...,
        description="Ranked list of recommended ML profiles for the detected hardware.",
    )
    warnings: list[str] = Field(
        ...,
        description="Hardware warnings that may affect ML workload performance.",
        examples=[
            ["Low system RAM (<8 GB). Heavy ML workloads may fail or swap heavily."]
        ],
    )
