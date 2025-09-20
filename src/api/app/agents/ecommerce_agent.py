import logging
import os
from os import environ

from typing import Optional

from dotenv import load_dotenv

from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPSsePlugin
from app.schemas.agent import AgentResponse


logger = logging.getLogger(__name__)


class SemanticKernelEcommerceAgent:
    """Refactored agent class. No network calls at import time."""

    def __init__(self, service: Optional[AzureChatCompletion] = None):
        load_dotenv()
        # Defer heavy setup to initialize()
        self.service = service
        self.search_plugin = None
        self.shopping_plugin = None
        self.inventory_plugin = None
        self.agent = None
        self.thread = None

    async def initialize(self):
        """Initialize connectors, plugins and sub agents.

        This method performs network operations and should be called from
        an application startup event.
        """
        # Lazy create service if not provided
        if self.service is None:
            # Validate required env vars
            required = [
                "AZURE_OPENAI_MODEL",
                "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_API_KEY",
                "MCP_SERVER_URL",
            ]
            missing = [v for v in required if v not in os.environ]
            if missing:
                raise RuntimeError(f"Missing required env vars: {missing}")

            self.service = AzureChatCompletion(
                service_id="chat",
                deployment_name=os.environ["AZURE_OPENAI_MODEL"],
                endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
            )

        # Create plugins
        self.search_plugin = MCPSsePlugin(
            name="search",
            url=f"{os.environ['MCP_SERVER_URL']}/search/sse",
        )
        self.shopping_plugin = MCPSsePlugin(
            name="shopping",
            url=f"{os.environ['MCP_SERVER_URL']}/shopping/sse",
        )
        self.inventory_plugin = MCPSsePlugin(
            name="inventory",
            url=f"{os.environ['MCP_SERVER_URL']}/inventory/sse",
        )

        # Connect plugins
        logger.info("Connecting product plugin...")
        await self.search_plugin.connect()
        logger.info("Connecting inventory plugin...")
        await self.inventory_plugin.connect()

        # Build sub-agents
        shopping_agent = ChatCompletionAgent(
            service=self.service,
            name='ShoppingAgent',
            instructions=(
                "Handles shopping cart updates, checkout, and payment workflows."
            ),
            plugins=[self.shopping_plugin],
        )

        search_agent = ChatCompletionAgent(
            service=self.service,
            name='SearchAgent',
            instructions=(
                "Handles lookup of games, listing games, search, finding the productID for a game and related suggestions."
            ),
            plugins=[self.search_plugin],
        )

        inventory_agent = ChatCompletionAgent(
            service=self.service,
            name='InventoryAgent',
            instructions=(
                "Uses the GUID identifier of the product (productId) to check inventory (stock) and warehouse info."
            ),
            plugins=[self.inventory_plugin],
        )

        # Supervisor
        self.agent = ChatCompletionAgent(
            service=self.service,
            name='EcommerceSupervisor',
            instructions=(
                "You are an ecommerce assistant that routes to available agents and never uses its own knowledge."
            ),
            plugins=[shopping_agent, search_agent, inventory_agent],
        )

    async def invoke(self, user_input: str, session_id: str):
        # Ensure plugins connected (no-op if already connected)
        if self.search_plugin:
            await self.search_plugin.connect()
        if self.inventory_plugin:
            await self.inventory_plugin.connect()

        response = await self.agent.get_response(messages=user_input, thread=self.thread)
        return self._get_agent_response(response.content)

    def _get_agent_response(self, content):
        # Simplified extraction
        message_text = ""
        inner = getattr(content, "inner_content", None)
        if inner and getattr(inner, "choices", None):
            for choice in inner.choices:
                if getattr(choice, "finish_reason", "") == "stop" and getattr(choice, "message", None):
                    message_text = getattr(choice.message, "content", "")
                    break

        return AgentResponse(
            content=message_text,
            is_task_complete=True,
            require_user_input=True,
        )
