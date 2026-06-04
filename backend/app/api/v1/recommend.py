"""Recommend endpoint -- POST /api/v1/recommend."""

from fastapi import APIRouter

from app.recommendation.engine import recommend_profiles
from app.schemas.diagnostic import DiagnosticReportSchema
from app.schemas.recommendation import RecommendationResponse

router = APIRouter()


@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    status_code=200,
    summary="Get ML framework recommendations based on hardware",
    description=(
        "Accept a diagnostic report and return a ranked list of recommended "
        "ML profiles based on detected hardware. Pure deterministic logic — "
        "no LLM calls."
    ),
    tags=["Recommendations"],
    responses={
        200: {"description": "Recommendations returned successfully"},
        422: {"description": "Invalid diagnostic report payload"},
    },
)
async def recommend(
    diagnostic_report: DiagnosticReportSchema,
) -> RecommendationResponse:
    """
    Accept a DiagnosticReport and return ranked ML framework recommendations.

    Rules are deterministic and based on:
    - GPU presence and VRAM capacity
    - Apple Silicon detection
    - System RAM availability
    """
    result = recommend_profiles(diagnostic_report)
    return RecommendationResponse(**result)
