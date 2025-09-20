from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.contents import ChatHistory
from datetime import datetime
import uuid
import os

from dotenv import load_dotenv
from enum import Enum
from typing import Optional


load_dotenv(override=True)


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class CosmosChatHistoryStore:
    def __init__(self, limit: int = 500):
        self._url = os.getenv("COSMOSDB_ENDPOINT")
        self._db_name = os.getenv("COSMOSDB_DATABASE")
        self._container_name = os.getenv("COSMOSDB_HISTORY_CONTAINER")
        self._limit = limit

        if not self._url or not self._db_name or not self._container_name:
            missing = [
                name
                for name, value in [
                    ("COSMOSDB_ENDPOINT", self._url),
                    ("COSMOSDB_DATABASE", self._db_name),
                    ("COSMOSDB_HISTORY_CONTAINER", self._container_name),
                ]
                if not value
            ]
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

        # Initialize lazily
        self._client: Optional[CosmosClient] = None
        self._container = None
        self._credential: Optional[DefaultAzureCredential] = None

    async def _ensure_container(self):
        """Ensure the Cosmos DB container is initialized."""
        if self._client is None:
            self._credential = DefaultAzureCredential()
            self._client = CosmosClient(self._url, credential=self._credential)
            database = self._client.get_database_client(self._db_name)
            self._container = database.get_container_client(self._container_name)

    async def load(self, session_id: str) -> ChatHistory:
        await self._ensure_container()
        chat_history = ChatHistory()
        query = "SELECT * FROM c WHERE c.sessionid = @sid"
        params = [{"name": "@sid", "value": session_id}]

        results = self._container.query_items(query, parameters=params, enable_cross_partition_query=True)

        async for item in results:
            role = item.get("role")
            if role == ChatRole.USER.value:
                chat_history.add_user_message(item["message"])
            elif role == ChatRole.ASSISTANT.value:
                chat_history.add_assistant_message(item["message"])
            elif role == ChatRole.SYSTEM.value:
                chat_history.add_system_message(item["message"])
            elif role == ChatRole.TOOL.value:
                chat_history.add_tool_message(item["message"])
        return chat_history

    async def add_message(
        self,
        history: ChatHistory,
        session_id: str,
        role: ChatRole,
        content: str,
        tool_call_id: Optional[str] = None,
        function_name: Optional[str] = None,
    ):
        await self._ensure_container()

        # Update ChatHistory based on role
        if role == ChatRole.USER:
            history.add_user_message(content)
        elif role == ChatRole.ASSISTANT:
            history.add_assistant_message(content)
        elif role == ChatRole.SYSTEM:
            history.add_system_message(content)
        elif role == ChatRole.TOOL:
            history.add_tool_message(content, tool_call_id=tool_call_id, function_name=function_name)
        else:
            raise ValueError(f"Unknown role: {role}")

        # Persist to Cosmos
        item = {
            "id": str(uuid.uuid4()),
            "sessionid": session_id,
            "message": content,
            "role": role.value,  # store as string
            "tool_call_id": tool_call_id,
            "function_name": function_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self._container.create_item(body=item)
