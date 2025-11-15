# app/stores/cosmos_sql_vector_store.py

import uuid
import os
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, List, Optional

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.core.credentials_async import AsyncTokenCredential

from semantic_kernel.connectors.ai.open_ai import AzureTextEmbedding


logger = logging.getLogger(__name__)


# --------------------------------------------------------
# Cache record stored in Cosmos DB
# --------------------------------------------------------
@dataclass
class CacheRecord:
    """
    Cosmos DB document schema for cached LLM responses:
        id: unique record id
        result: JSON result {"content": ..., "references": ...}
        prompt: original prompt text (we embed it at write time)
    """
    id: Optional[str]
    result: str
    prompt: Optional[str] = None


# --------------------------------------------------------
# Search result wrapper
# --------------------------------------------------------
@dataclass
class SearchResultItem:
    score: float
    record: CacheRecord


class _SearchResultsWrapper:
    """
    Matches Semantic Kernel-style vector search output.
    """

    def __init__(self, results: AsyncIterator[SearchResultItem]):
        self.results = results


# --------------------------------------------------------
# Cosmos DB SQL Vector Store (NoSQL)
# --------------------------------------------------------
class CosmosDBSqlVectorStore:
    """
    A clean custom vector store supporting:
        - upsert(CacheRecord)
        - search(query_text)
        - Cosmos DB VectorDistance queries

    This does NOT depend on Semantic Kernel memory stores.
    """

    def __init__(self):
        # -----------------------------
        # Environment setup
        # -----------------------------
        self._url = os.getenv("COSMOSDB_ENDPOINT")
        self._db_name = os.getenv("COSMOSDB_DATABASE")
        self._container_name = os.getenv("COSMOSDB_CACHE_CONTAINER", "llm_responses")

        missing = [
            name for name, value in [
                ("COSMOSDB_ENDPOINT", self._url),
                ("COSMOSDB_DATABASE", self._db_name),
                ("COSMOSDB_CACHE_CONTAINER", self._container_name)
            ]
            if not value
        ]
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

        # -----------------------------
        # Embedding service
        # -----------------------------
        self._embedding_generator = AzureTextEmbedding(
            service_id="embedder",
            deployment_name=os.environ["AZURE_OPENAI_EMBEDDING_MODEL"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )

        # -----------------------------
        # Lazily-initialized Cosmos client + container
        # -----------------------------
        self._client: Optional[CosmosClient] = None
        self._container = None
        self._credential: Optional[AsyncTokenCredential] = None

    # --------------------------------------------------------
    # Initialization helpers
    # --------------------------------------------------------
    async def _ensure_container(self):
        if self._client is None:
            logger.debug("Initializing Cosmos DB client + container...")
            self._credential = DefaultAzureCredential()
            self._client = CosmosClient(self._url, credential=self._credential)

            db = self._client.get_database_client(self._db_name)
            self._container = db.get_container_client(self._container_name)

    async def ensure_collection_exists(self):
        """Provided for parity—container already created via Bicep."""
        await self._ensure_container()

    # --------------------------------------------------------
    # Embeddings
    # --------------------------------------------------------
    async def _embed_text(self, text: str) -> List[float]:
        eg = self._embedding_generator

        if hasattr(eg, "generate_embeddings_async"):
            vectors = await eg.generate_embeddings_async([text])
            vector = vectors[0]
        else:
            vectors = await eg.generate_embeddings([text])
            vector = vectors[0]

        # FIX: Ensure vector is JSON-serializable (Cosmos DB requires Python list)
        return vector.tolist() if hasattr(vector, "tolist") else vector

    # --------------------------------------------------------
    # UPSERT
    # --------------------------------------------------------
    async def upsert(self, record: CacheRecord):
        """Writes one CacheRecord → Cosmos vector index."""
        await self._ensure_container()

        prompt_text = record.prompt or ""
        prompt_vector = await self._embed_text(prompt_text)

        doc_id = record.id or str(uuid.uuid4())

        doc = {
            "id": doc_id,
            "result": record.result,
            "prompt": prompt_vector,
            "promptText": prompt_text,  # optional, helpful for debugging
        }

        logger.debug(f"[CosmosVectorStore] Upsert document id={doc_id}")
        await self._container.upsert_item(doc)

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------
    async def search(
        self,
        query: str,
        *,
        vector_property_name: str,
        top: int = 1,
    ) -> _SearchResultsWrapper:
        """
        Performs vector search using Cosmos SQL VectorDistance().
        Cosmos DB requires the full expression in ORDER BY (cannot use alias).
        """
        await self._ensure_container()

        # Convert embedding → Python list, not ndarray
        query_vector = await self._embed_text(query)

        # FIX: Must repeat full VectorDistance expression in ORDER BY.
        sql = (
            "SELECT TOP @k c.id, c.result, c.promptText, "
            f"VectorDistance(c.{vector_property_name}, @qv) AS score "
            "FROM c "
            f"ORDER BY VectorDistance(c.{vector_property_name}, @qv)"
        )

        params = [
            {"name": "@k", "value": top},
            {"name": "@qv", "value": query_vector},
        ]

        items_iter = self._container.query_items(
            query=sql,
            parameters=params
        )

        async def _gen() -> AsyncIterator[SearchResultItem]:
            async for doc in items_iter:
                yield SearchResultItem(
                    score=doc["score"],
                    record=CacheRecord(
                        id=doc["id"],
                        result=doc["result"],
                        prompt=doc.get("promptText"),
                    ),
                )

        return _SearchResultsWrapper(_gen())
