"""Feedback endpoints -- POST /api/v1/uninstall/feedback."""

from fastapi import APIRouter

from app.api.deps import DB
from app.models.feedback import UninstallFeedback
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter()


@router.post(
    "/uninstall/feedback",
    response_model=FeedbackResponse,
    status_code=201,
    summary="Submit uninstall feedback",
    description="Save user uninstall feedback (rating, reasons, comments, optional email) to the database.",
    tags=["Feedback"],
    responses={
        201: {"description": "Feedback saved successfully"},
        422: {"description": "Invalid input payload"},
    },
)
async def submit_feedback(
    feedback_in: FeedbackCreate,
    db: DB,
) -> UninstallFeedback:
    """
    Save feedback to the database.
    """
    feedback = UninstallFeedback(
        rating=feedback_in.rating,
        reasons=feedback_in.reasons,
        comments=feedback_in.comments,
        email=feedback_in.email,
    )
    db.add(feedback)
    await db.flush()
    return feedback
