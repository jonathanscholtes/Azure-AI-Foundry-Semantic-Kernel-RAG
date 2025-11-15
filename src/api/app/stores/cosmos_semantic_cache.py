# app/stores/cosmos_semantic_cache.py

import json
from typing import List, Optional

from app.stores.cosmos_sql_vector_store import (
    CosmosDBSqlVectorStore,
    CacheRecord,
)


class CosmosSemanticCache:
    """
    Manual semantic cache with Cosmos DB vector search.

    Responsibilities:
        - Generate embeddings using AzureTextEmbedding
        - Query Cosmos SQL VectorDistance index for similar prompts
        - Store new prompt->response pairs in Cosmos
    """

    def __init__(
        self,
        score_threshold: float = 0.20,
    ):
        self.vector_store = CosmosDBSqlVectorStore()

        self.score_threshold = score_threshold



    async def get_similar(self, prompt: str) -> Optional[dict]:
        """
        Look up whether a similar prompt was asked before.
        - Generates an embedding for the prompt
        - Performs VectorDistance search in Cosmos DB
        - Returns {"content": ..., "references": ...} or None
        """

        await self.vector_store.ensure_collection_exists()

        # Search directly using prompt text (collection will embed internally)
        results = await self.vector_store.search(
            query=prompt,
            vector_property_name="prompt",
            top=1
        )

        async for result in results.results:
            if result.score < self.score_threshold:
                return json.loads(result.record.result)

        return None

 
    async def store(self, prompt: str, content: str, references: List[str]):
        """
        Store new prompt → LLM result pair in Cosmos DB.
        """

        await self.vector_store.ensure_collection_exists()

        payload = {
            "content": content,
            "references": references,
        }

        record = CacheRecord(
            id=None,
            prompt=prompt,            # raw text — vector is generated inside upsert()
            result=json.dumps(payload)
        )

        await self.vector_store.upsert(record)
