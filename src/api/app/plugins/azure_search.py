import os
import logging
from typing import List, Dict
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from semantic_kernel.functions import kernel_function

load_dotenv(override=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AzureSearchPlugin:
    def __init__(self):
        logger.info("Initializing Azure Search client...")

        self.endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
        self.index_name = os.getenv("AZURE_AI_SEARCH_INDEX")
        self.vector_field = os.getenv("AZURE_SEARCH_VECTOR_FIELD")

        missing = [
            name
            for name, value in [
                ("AZURE_AI_SEARCH_ENDPOINT", self.endpoint),
                ("AZURE_AI_SEARCH_INDEX", self.index_name),
                ("AZURE_SEARCH_VECTOR_FIELD", self.vector_field),
            ]
            if not value
        ]

        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

        self.credential = DefaultAzureCredential()
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential,
        )

    def hybrid_search(self, query: str, top: int = 5) -> List[Dict]:
        """Perform hybrid search (keyword + vector) on the index."""
        logger.info(f"Performing hybrid search for: {query}")

        results = self.search_client.search(
            search_text=query,
            vector_queries=[
                VectorizableTextQuery(
                    text=query,
                    k_nearest_neighbors=50,
                    fields=self.vector_field,
                )
            ],
            top=top,
            select=["title", "content", "pageNumber"],
        )
        return self._format_results(results)

    @kernel_function
    def search(self, query: str, top: int = 5) -> str:
        """Document search for agents with Markdown output."""
        logger.info(f"Tool called: hybrid_search(query='{query}', top={top})")
        try:
            results = self.hybrid_search(query, top)
            return self._format_results_as_markdown(results, title="Hybrid Search Results")
        except Exception as e:
            logger.error(f"Error during hybrid_search: {e}")
            return f"Error: {str(e)}"

    def _format_results(self, results) -> List[Dict]:
        """Format search results as a list of dictionaries."""
        return [
            {
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "pageNumber": r.get("pageNumber", ""),
            }
            for r in results
        ]

    def _format_results_as_markdown(self, results: List[Dict], title: str = "Results") -> str:
        """Convert results to Markdown string for agent-friendly output."""
        if not results:
            return f"**{title}**\n\nNo results found."
        
        md = f"**{title}**\n\n"
        for i, r in enumerate(results, start=1):
            md += f"**{i}. {r['title']} (Page {r['pageNumber']})**\n"
            md += f"{r['content']}\n\n"
        return md
