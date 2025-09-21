import logging
import os
from os import environ
from typing import Any, Dict, Optional
from functools import partial

from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.contents import ChatMessageContent, ChatHistory
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

from app.schemas.agent import AgentResponse
from app.history.cosmos_chat_history import CosmosChatHistoryStore, ChatRole

load_dotenv()
logger = logging.getLogger(__name__)


class BaseAgent:
    def __init__(self, kernel: Optional[Kernel] = None):
        """
        BaseAgent holds shared components for all agents:
        - kernel (can be per-agent)
        - agent (ChatCompletionAgent)
        - history_store
        Per-request state (session_id, chat_history) should be passed to methods.
        """
        self.kernel = kernel
        self.agent: Optional[ChatCompletionAgent] = None
        self.history_store: Optional[CosmosChatHistoryStore] = None
 

    async def initialize(self):
        """
        Initialize the kernel and history store if not provided.
        Uses async DefaultAzureCredential and passes token directly.
        """
        if self.kernel is None:
            from azure.identity.aio import DefaultAzureCredential

            async with DefaultAzureCredential() as credential:
                token = (await credential.get_token(
                    "https://cognitiveservices.azure.com/.default"
                )).token

            environ.update({
                "OPENAI_API_TYPE": "azure_ad",
                "AZURE_OPENAI_API_KEY": token,
                "AZURE_OPENAI_AD_TOKEN": token
            })

            # Validate required env vars
            required = [
                "AZURE_OPENAI_MODEL",
                "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_API_KEY",
                "AZURE_OPENAI_API_VERSION"
            ]
            missing = [v for v in required if v not in os.environ]
            if missing:
                raise RuntimeError(f"Missing required environment variables: {missing}")

            self.kernel = Kernel()
            self.kernel.add_service(AzureChatCompletion(
                service_id="chat",
                deployment_name=os.environ["AZURE_OPENAI_MODEL"],
                endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_API_KEY"]
            ))

        # Initialize history store
        self.history_store = CosmosChatHistoryStore()

    async def on_intermediate_message(self, agent_result, session_id: str, response_id:str, chat_history: ChatHistory,metadata: Optional[Dict[str, Any]] = None):
        """
        Thread-safe handler for intermediate messages.
        Persists assistant content and tool outputs per request.
        """
        # Persist assistant content
        content = agent_result.content
        if content:
            content_text = content.content if isinstance(content, ChatMessageContent) else str(content)
            await self.history_store.add_message(chat_history, session_id, response_id, ChatRole.ASSISTANT, content_text, metadata=metadata)

        # Persist tool outputs
        for item in getattr(agent_result, "items", []):
            tool_call_id = getattr(item, "call_id", None) or getattr(item, "id", None)
            if not tool_call_id:
                continue

            function_name = getattr(item, "function_name", "N/A")
            result_content = getattr(item, "result", item)

            if isinstance(result_content, list):
                tool_text = "\n".join([getattr(c, "text", str(c)) for c in result_content])
            elif hasattr(result_content, "text"):
                tool_text = result_content.text
            else:
                tool_text = str(result_content)

            if function_name in tool_text:
                continue

            logger.debug(f"Tool invocation: {function_name}")
            logger.debug(f"Tool output: {tool_text}")

            await self.history_store.add_message(
                chat_history,
                session_id,
                response_id,
                ChatRole.ASSISTANT,
                content=tool_text,
                tool_call_id=tool_call_id,
                function_name=function_name,
                metadata=metadata
            )