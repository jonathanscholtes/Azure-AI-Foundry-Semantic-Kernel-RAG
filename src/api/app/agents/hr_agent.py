import logging
import os
from os import environ

from typing import Optional

from dotenv import load_dotenv

from semantic_kernel import Kernel
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

from app.schemas.agent import AgentResponse
from app.evaluations.evaluation import EvaluationEngine
from app.evaluations.cosmos_evaluation_store import CosmosEvaluationStore
from app.plugins.azure_search import AzureSearchPlugin
from app.history.cosmos_chat_history import CosmosChatHistoryStore, ChatRole
from app.agents.agent import BaseAgent

import uuid

load_dotenv()

logger = logging.getLogger(__name__)

class SemanticKernelHRAgent(BaseAgent):

    def __init__(self, kernel: Optional[AzureChatCompletion] = None):
        
        # Defer heavy setup to initialize()
        super().__init__(kernel)
        self.evaluation_engine = None
        self.evaluation_store = None
        

    async def initialize(self):
        
        await super().initialize()

        instructions = """You are an HR assistant. You help employees with HR-related queries.
            - Use the 'search' plugin to look up information in the HR knowledge base.
            - Do not make up answers. If you cannot find the answer, say "I don't know"."""

        search_plugin = AzureSearchPlugin()

        self.agent = ChatCompletionAgent(
        kernel=self.kernel, 
        name="HRAssistant", 
        instructions=instructions,
        plugins=[search_plugin, ])
    
        self.evaluation_engine = EvaluationEngine()
        self.evaluation_store = CosmosEvaluationStore()



    
    def _run_evaluation(self, user_input: str, response: str, request_id: str):
        if not request_id:
            logger.warning("No request_id set; skipping evaluation storage.")
            return

        evaluation = self.evaluation_engine.evaluate_response(user_input, response, self.chat_history)
        if not evaluation:
            logger.info("No evaluation generated; skipping storage.")
            return

        try:
            self.evaluation_store.store_evaluation(
                session_id=self.session_id,
                response_id=self.request_id,
                user_query=user_input,
                response=response,
                evaluation=evaluation,
                metadata={"agent": "hr_agent"}
            )
            logger.info(f"Stored evaluation for request_id {self.request_id}")
        except Exception as e:
            logger.error(f"Failed to store evaluation: {e}")



    async def invoke(self, user_input: str, session_id: str):
        
        
        request_id = str(uuid.uuid4())

        # make thread safe
        self.session_id = session_id

        self.chat_history = await self.history_store.load(session_id)

        
        await self.history_store.add_message(self.chat_history,session_id, ChatRole.USER, user_input)

        final_response = None
        async for result in self.agent.invoke(messages=self.chat_history, on_intermediate_message=super().on_intermediate_message):
            final_response = result 

        # Run only if eval flag is set
        self._run_evaluation(user_input, final_response.content.content if final_response else "",request_id)

        await self.history_store.add_message(self.chat_history,session_id, ChatRole.ASSISTANT, final_response.content.content)
       
        return AgentResponse(
                content=final_response.content.content,
                is_task_complete=True,
                require_user_input=True,
            )