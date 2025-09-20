from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv
from typing import Any, Dict, Optional


load_dotenv(override=True)

class EvaluationStore:
    async def store_evaluation(self, session_id: str, response_id: str, user_query: str, response: str, evaluation: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        raise NotImplementedError("store_evaluation must be implemented by subclasses")

class CosmosEvaluationStore(EvaluationStore):
    def __init__(self):
        self._url = os.getenv("COSMOSDB_ENDPOINT")
        self._db_name = os.getenv("COSMOSDB_DATABASE")
        self._container_name = os.getenv("COSMOSDB_EVALUATIONS_CONTAINER", "evaluations")

        if not self._url or not self._db_name:
            missing = [
                name
                for name, value in [
                    ("COSMOSDB_ENDPOINT", self._url),
                    ("COSMOSDB_DATABASE", self._db_name),
                ]
                if not value
            ]
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

        # Initialize lazily
        self._client: Optional[CosmosClient] = None
        self._container = None
        self._credential: Optional[DefaultAzureCredential] = None

    async def _ensure_container(self):
        """Ensure the Cosmos DB container is initialized with managed identity."""
        if self._client is None:
            self._credential = DefaultAzureCredential()
            self._client = CosmosClient(self._url, credential=self._credential)
            database = self._client.get_database_client(self._db_name)
            self._container = database.get_container_client(self._container_name)

    async def store_evaluation(self, session_id: str, response_id: str, user_query: str, response: str, evaluation: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        await self._ensure_container()

        item = {
            "id": str(uuid.uuid4()),
            "sessionid": session_id,
            "response_id": response_id,
            "user_query": user_query,
            "response": response,
            "evaluation": evaluation,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self._container.create_item(body=item)
