import json
from dotenv import load_dotenv
from os import environ
from semantic_kernel.contents import ChatHistory


load_dotenv(override=True)

from azure.ai.evaluation import GroundednessEvaluator, CoherenceEvaluator, RelevanceEvaluator
from typing import Dict, Any


class EvaluationEngine:
    """Wraps model-based evaluators and returns structured results."""

    def __init__(self):
        model_config = {
            "azure_endpoint": environ.get("AZURE_OPENAI_ENDPOINT"),
            "api_key": environ.get("AZURE_OPENAI_API_KEY"),
            "azure_deployment": environ.get("AZURE_OPENAI_MODEL"),
            "api_version": environ.get("AZURE_OPENAI_API_VERSION"),
        }

        self.groundedness_evaluator = GroundednessEvaluator(model_config=model_config)
        self.coherence_evaluator = CoherenceEvaluator(model_config=model_config)
        self.relevance_evaluator = RelevanceEvaluator(model_config=model_config)
    

    def _get_context_from_history(self, history: ChatHistory) -> str:
        context = ""
        for message in history.messages:
            if message.role != "assistant":
                continue
            context += message.content + "\n"
        return context

    def evaluate_from_history(self, user_query: str, response: str, history: ChatHistory) -> Dict[str, Any]:
        context = self._get_context_from_history(history)
        return self.evaluate(user_query, response, context)

    def evaluate(self, user_query: str, response: str, context: str = "") -> Dict[str, Any]:
        groundedness_result = self.groundedness_evaluator(
            query=user_query,
            response=response,
            context=context,
        )
        coherence_result = self.coherence_evaluator(
            query=user_query,
            response=response,
            context=context,
        )

        relevance_result = self.relevance_evaluator(
            query=user_query,
            response=response,
        )

        return {
            "groundedness": groundedness_result,
            "coherence": coherence_result,
            "relevance": relevance_result,
        }
