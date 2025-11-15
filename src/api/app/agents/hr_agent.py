import logging
import uuid
from functools import partial
from typing import Any, Dict, Optional
import json
import re

from semantic_kernel.agents import ChatCompletionAgent
from app.schemas.agent import AgentResponse
from app.evaluations.evaluation import EvaluationEngine
from app.evaluations.cosmos_evaluation_store import CosmosEvaluationStore
from app.plugins.azure_search import AzureSearchPlugin
from app.agents.agent import BaseAgent
from app.history.cosmos_chat_history import ChatRole


from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class SemanticKernelHRAgent(BaseAgent):
    def __init__(self, kernel = None):
        super().__init__(kernel)

        self.evaluation_engine = None
        self.evaluation_store = None
        self.agent_name = "HR_Agent"

    async def initialize(self):
        await super().initialize()

        instructions = (
            """You are an HR assistant. Help employees with HR-related queries.

                1. Context:
                - Use the 'search' plugin to look up HR knowledge base documents.
                - Do not make up answers. If you cannot find the answer, say "I don't know".

                2. Output Rules:
                - Return ONLY a valid JSON object.
                - Must strictly follow this structure:

                {
                "content": str,
                "references": [str]
                }

                3. Output Field Descriptions:
                - "content": must include your full answer in HTML
                - "references": List of titles of source documents referenced in the answer.

                4. Additional Notes:
                - Maintain a neutral, professional tone at all times.
                - The 'references' field must include the **exact 'title' fields** from retrieved documents.
                - Do not modify, shorten, or omit file extensions.
                - If no documents are retrieved, return an empty list.
                - If you cannot find the answer, respond with "I don't know" in the 'content' field and an empty list in 'references'.
                """
        )

        search_plugin = AzureSearchPlugin()

        self.agent = ChatCompletionAgent(
            kernel=self.kernel,
            name=self.agent_name,
            instructions=instructions,
            plugins=[search_plugin],
        )

        self.evaluation_engine = EvaluationEngine()
        self.evaluation_store = CosmosEvaluationStore()



    async def  _run_evaluation(self, user_input: str, response: str, session_id: str, request_id: str, chat_history,
                               metadata: Optional[Dict[str, Any]] = None):
       

        if not request_id:
            logger.warning("No request_id set; skipping evaluation storage.")
            return

        evaluation = self.evaluation_engine.evaluate_from_history(user_input, response, chat_history)

        if not evaluation:
            logger.info("No evaluation generated; skipping storage.")
            return

        try:
            await self.evaluation_store.store_evaluation(
                session_id=session_id,
                response_id=request_id,
                user_query=user_input,
                response=response,
                evaluation=evaluation,
                metadata=metadata
            )
            logger.info(f"Stored evaluation for request_id {request_id}")
        except Exception as e:
            logger.error(f"Failed to store evaluation: {e}")


    async def invoke(self, user_input: str, session_id: str) -> AgentResponse:
        """
        Thread-safe, per-request agent invocation.
        Includes semantic cache lookup + store.
        """
        response_id = str(uuid.uuid4())
        chat_history = await self.history_store.load(session_id)

        metadata = {"agent": self.agent_name}

        # ----------------------------------------------------------------------
        # 1. SEMANTIC CACHE LOOKUP (returns content + references if hit)
        # ----------------------------------------------------------------------
        if self.semantic_cache:
            cached = await self.semantic_cache.get_similar(user_input)

            if cached:
                logger.info(f"[CACHE HIT] Returning cached response for session={session_id}")

                # Save assistant message into history so transcript stays consistent
                await self.history_store.add_message(
                    chat_history, session_id, response_id,
                    ChatRole.ASSISTANT,
                    cached["content"],
                    metadata=metadata,
                )

                return AgentResponse(
                    content=cached["content"],
                    references=cached.get("references", []),
                    response_id=response_id,
                    is_task_complete=True,
                    require_user_input=True,
                )

        logger.info("[CACHE MISS] Proceeding with LLM call.")

        # ----------------------------------------------------------------------
        # 2. Add user message to history
        # ----------------------------------------------------------------------
        await self.history_store.add_message(
            chat_history, session_id, response_id,
            ChatRole.USER, user_input, metadata=metadata
        )

        # ----------------------------------------------------------------------
        # 3. Invoke the agent with tool support
        # ----------------------------------------------------------------------
        intermediate_handler = partial(
            self.on_intermediate_message,
            session_id=session_id,
            response_id=response_id,
            chat_history=chat_history,
            metadata=metadata,
        )

        final_response = None
        async for result in self.agent.invoke(
            messages=chat_history,
            on_intermediate_message=intermediate_handler
        ):
            final_response = result

        # ----------------------------------------------------------------------
        # 4. Parse final LLM response
        # ----------------------------------------------------------------------
        content = ""
        references = []

        if final_response:
            raw_output = final_response.content.content
            clean_content = re.sub(r"^```json\s*|```$", "", raw_output.strip(), flags=re.MULTILINE)

            try:
                parsed = json.loads(clean_content)
                content = parsed.get("content", "")
                references = parsed.get("references", [])
            except json.JSONDecodeError:
                logger.warning("Model output not valid JSON; using raw content.")
                content = clean_content
                references = []

            # ------------------------------------------------------------------
            # 5. Run your evaluation engine
            # ------------------------------------------------------------------
            await self._run_evaluation(
                user_input, content, session_id, response_id, chat_history, metadata=metadata
            )

            # ------------------------------------------------------------------
            # 6. Save assistant response to chat history
            # ------------------------------------------------------------------
            await self.history_store.add_message(
                chat_history, session_id, response_id,
                ChatRole.ASSISTANT, content, metadata=metadata
            )

            # ------------------------------------------------------------------
            # 7. STORE IN SEMANTIC CACHE
            # ------------------------------------------------------------------
            if self.semantic_cache:
                logger.info("Storing new response in semantic cache...")
                await self.semantic_cache.store(
                    prompt=user_input,
                    content=content,
                    references=references
                )

        # ----------------------------------------------------------------------
        # 8. Return structured response to the caller
        # ----------------------------------------------------------------------
        return AgentResponse(
            content=content,
            references=references,
            response_id=response_id,
            is_task_complete=True,
            require_user_input=True,
        )