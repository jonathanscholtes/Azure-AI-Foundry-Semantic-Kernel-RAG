from pydantic import BaseModel


class AgentRequest(BaseModel):
    user_input: str
    session_id: str


class AgentResponse(BaseModel):
    content: str
    response_id: str
    is_task_complete: bool
    require_user_input: bool
