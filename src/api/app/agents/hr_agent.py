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
from ..evaluations.evaluation import EvaluationEngine, EvaluationStore
from ..plugins import SearchPlugin
from ..history import CosmosChatHistoryStore,ChatRole

logger = logging.getLogger(__name__)

class SemanticKernelHRAgent:

    def __init__(self, kernel: Optional[AzureChatCompletion] = None):
        load_dotenv()
        # Defer heavy setup to initialize()
        self.kernel = kernel
        self.agent = None
        self.thread = None
        self.history_store = CosmosChatHistoryStore()
        self.chat_history = None
        self.session_id = None
        self.request_id = None
        

    async def initialize(self):
        if self.kernel is None:
            # Validate required env vars
            required = [
                "AZURE_OPENAI_MODEL",
                "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_API_KEY"
            ]
            missing = [v for v in required if v not in os.environ]
            if missing:
                raise RuntimeError(f"Missing required env vars: {missing}")
            
            kernel = Kernel()

            kernel.add_service(AzureChatCompletion(
                service_id="chat",
                deployment_name=os.environ["AZURE_OPENAI_MODEL"],
                endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
            ))


            instructions = """You are an HR assistant. You help employees with HR-related queries.
            Use the 'search' plugin to look up information in the HR knowledge base. Do not make up answers. If you cannot find the answer, say "I don't know"."""

            search_plugin = SearchPlugin()

            agent = ChatCompletionAgent(
            kernel=kernel, 
            name="HR Assistant", 
            instructions=instructions,
            plugins=[search_plugin, ]
        )


    async def __on_intermediate_message(self,agent_result):

    
        # Capture assistant content
        content = agent_result.content
        if content:
            content_text = content.content if isinstance(content, ChatMessageContent) else str(content)
            await self.history_store.add_message(self.chat_history, self.session_id, ChatRole.ASSISTANT, content_text)

        # Capture tool calls and results
        for item in getattr(agent_result, "items", []):
            tool_call_id = getattr(item, "call_id", None) or getattr(item, "id", None)
            if not tool_call_id:
                continue  # skip if no call_id

            # Function name for bookkeeping
            function_name = getattr(item, "function_name", "N/A")

            # Print the invocation (DEBUG ONLY — not persisted)
            if hasattr(item, "arguments"):
                print(f"Tool invocation: {function_name}({item.arguments})")

            # Extract the result content
            result_content = getattr(item, "result", item)
            if isinstance(result_content, list):
                tool_text = "\n".join([c.text if hasattr(c, "text") else str(c) for c in result_content])
            elif hasattr(result_content, "text"):
                tool_text = result_content.text
            else:
                tool_text = str(result_content)

            if function_name in tool_text:
                continue
            
            #print(f"Tool call ID: {tool_call_id}")
            #print(f"Tool Function Name: {function_name}")
            print(f"Tool output: {tool_text}")

            await self.history_store.add_message(
                self.chat_history,
                self.session_id,
                ChatRole.ASSISTANT,
                content=tool_text,
                tool_call_id=tool_call_id,
                function_name=function_name
            )

       
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

    async def invoke(self, user_input: str, session_id: str):
        
    
        self.chat_history = await self.history_store.load(session_id)

        await self.history_store.add_message(self.chat_history,session_id, ChatRole.USER, user_input)

        final_response = None
        async for result in self.agent.invoke(messages=self.chat_history, on_intermediate_message=self.__on_intermediate_message):
            final_response = result 

        return self._get_agent_response(final_response)