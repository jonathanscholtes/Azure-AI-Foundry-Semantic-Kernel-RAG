from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    session_id: str
    response_id: str
    feedback: str
