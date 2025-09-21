
import logging
import os
from os import environ

from semantic_kernel import Kernel
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from app.schemas.agent import AgentResponse
from app.history.cosmos_chat_history import CosmosChatHistoryStore,ChatRole
from semantic_kernel.contents import ChatHistory
from typing import Optional
from app.schemas.agent import AgentResponse
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential


load_dotenv()

class BaseAgent:

    def __init__(self, kernel: Optional[AzureChatCompletion] = None):
        
        # Defer heavy setup to initialize()
        self.kernel = kernel
        self.agent = None
        self.thread = None
        self.history_store:CosmosChatHistoryStore = None
        self.chat_history:ChatHistory = None
        self.session_id = None
        self.request_id = None

    async def initialize(self):
        if self.kernel is None:

            credential = DefaultAzureCredential()
            token = (await credential.get_token("https://cognitiveservices.azure.com/.default")).token

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
                raise RuntimeError(f"Missing required env vars: {missing}")
            
            kernel = Kernel()

            kernel.add_service(AzureChatCompletion(
                service_id="chat",
                deployment_name=os.environ["AZURE_OPENAI_MODEL"],
                endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
            ))

            self.history_store = CosmosChatHistoryStore()

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