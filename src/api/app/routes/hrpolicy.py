from fastapi import APIRouter, HTTPException
import logging

from ..agents.hr_agent import SemanticKernelHRAgent
from ..schemas.agent import AgentRequest, AgentResponse

router = APIRouter()

logger = logging.getLogger("api.routes.hrpolicy")

# Initialize a single agent instance to be used by the router.
agent = SemanticKernelHRAgent()


@router.on_event("startup")
async def _startup_event():
    logger.info("Initializing agent from routes startup...")
    await agent.initialize()
    logger.info("Agent initialized.")


@router.post("/hrpolicy/agent", response_model=AgentResponse)
async def handle_request(payload: AgentRequest):
    try:
        logger.info(f'handle_request user_input{payload.user_input}')
        result = await agent.invoke(payload.user_input, payload.session_id)
        logger.info(f'Results:{result}')
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def get_status() -> str:
    logger.info("**Logging - RUNNING**")
    return "running"