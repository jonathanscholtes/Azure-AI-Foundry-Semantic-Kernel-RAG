# app/stores/cosmos_vector_cache_store.py

import os
from semantic_kernel.connectors.ai.open_ai import AzureTextEmbedding
from app.semantic_cache.prompt_cache_filter import PromptCacheFilter, CacheRecord
from semantic_kernel.filters import FilterTypes
from azure.identity.aio import DefaultAzureCredential

from app.stores.cosmos_sql_vector_store import CosmosDBSqlVectorStore

 
class CosmosVectorSemanticCacheStore:
    def __init__(self, kernel):
        self.kernel = kernel

        self._url = os.getenv("COSMOSDB_ENDPOINT")
        self._db_name = os.getenv("COSMOSDB_DATABASE")
        self._container_name = os.getenv("COSMOSDB_CACHE_CONTAINER", "llm_responses")
        

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

    def attach(self):
        """
        Attaches Cosmos SQL vector store + semantic cache filters to the SK kernel.
        """


        embedding = AzureTextEmbedding(
            service_id="embedder",
            deployment_name=os.environ["AZURE_OPENAI_EMBEDDING_MODEL"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"]
        )

        self.kernel.add_service(embedding)
   


        vector_store = CosmosDBSqlVectorStore(
            cosmos_endpoint=self._url,
            credential=DefaultAzureCredential(),
            database_name=self._db_name,
            container_name=self._container_name,
            embedding_generator=embedding,
        )

        cache_filter = PromptCacheFilter(
            vector_store=vector_store,
            score_threshold=0.20,  # lower = stricter semantic match
        )

       
        self.kernel.add_filter(FilterTypes.PROMPT_RENDERING, cache_filter.on_prompt_render)
        self.kernel.add_filter(FilterTypes.FUNCTION_INVOCATION, cache_filter.on_function_invocation)
