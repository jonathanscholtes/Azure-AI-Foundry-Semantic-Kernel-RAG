from fastapi import APIRouter, HTTPException
import logging
from app.stores.feedback_store import FeedbackStore
from app.schemas.feedback import FeedbackRequest


router = APIRouter()

logger = logging.getLogger("api.routes.feedback")

feedback_store = FeedbackStore()

@router.post("/feedback")
async def submit_feedback(feedback_request: FeedbackRequest):
    """Submit feedback for a specific session and response."""
    if not feedback_request:
        raise HTTPException(status_code=400, detail="Feedback cannot be empty.")
    try:
        feedback_dict = feedback_request.model_dump()
        await feedback_store.add_feedback(feedback_dict)
        return {"message": "Feedback submitted successfully.", "entry": feedback_dict}
    except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))