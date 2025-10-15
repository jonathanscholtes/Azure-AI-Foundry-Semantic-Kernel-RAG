import os
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

import uuid
import os

from dotenv import load_dotenv
from enum import Enum
from typing import Any, Dict, Optional

load_dotenv(override=True)

class FeedbackStore:
    def __init__(self):
        self._url = os.getenv("COSMOSDB_ENDPOINT")
        self._db_name = os.getenv("COSMOSDB_DATABASE")
        self._container_name = os.getenv("COSMOSDB_FEEDBACK_CONTAINER")


        if not self._url or not self._db_name or not self._container_name:
            missing = [
                name
                for name, value in [
                    ("COSMOSDB_ENDPOINT", self._url),
                    ("COSMOSDB_DATABASE", self._db_name),
                    ("COSMOSDB_FEEDBACK_CONTAINER", self._container_name),
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

    async def add_feedback(self, feedback_entry: dict):
        """Add a feedback entry to the Cosmos DB container."""
        await self._ensure_container()
        feedback_entry['id'] = str(uuid.uuid4())
        await self._container.create_item(body=feedback_entry)
            
       