import logging
from dataclasses import dataclass, field
from typing import Annotated, Awaitable, Callable
from uuid import uuid4

from semantic_kernel.data.vector import (
    VectorStore,
    VectorStoreCollection,
    VectorStoreField,
    vectorstoremodel
)
from semantic_kernel.filters import (
    PromptRenderContext,
    FunctionInvocationContext
)
from semantic_kernel.functions import FunctionResult

logger = logging.getLogger(__name__)

COLLECTION_NAME = "llm_responses"
RECORD_ID_KEY = "cache_record_id"


@vectorstoremodel(collection_name=COLLECTION_NAME)
@dataclass
class CacheRecord:
    result: Annotated[str, VectorStoreField("data", is_full_text_indexed=True)]
    prompt: Annotated[str | None, VectorStoreField("vector", dimensions=1536)] = None
    id: Annotated[str, VectorStoreField("key")] = field(default_factory=lambda: str(uuid4()))


class PromptCacheFilter:
    """
    Safe semantic caching for ChatCompletionAgent + tool calling.
    Only caches FINAL assistant responses. Skips tools.
    """

    def __init__(self, vector_store: VectorStore, score_threshold: float = 0.20):
        if vector_store.embedding_generator is None:
            raise ValueError("Vector store must have an embedding generator.")

        self.vector_store = vector_store
        self.collection: VectorStoreCollection[str, CacheRecord] = (
            vector_store.get_collection(record_type=CacheRecord)
        )
        self.score_threshold = score_threshold

        logger.info(f"PromptCacheFilter initialized (threshold={score_threshold})")

    # ----------------------------------------------------------------------
    # BEFORE LLM RUNS: Try to READ from cache
    # ----------------------------------------------------------------------
    async def on_prompt_render(self, context: PromptRenderContext, next):
        await next(context)

        await self.collection.ensure_collection_exists()

        # --------- FIX #1: Inject prompt for ChatCompletionAgent ----------
        if not context.rendered_prompt:
            context.rendered_prompt = getattr(context.kernel, "saved_user_prompt", "")

        if not context.rendered_prompt:
            logger.debug("Semantic cache: No rendered prompt found.")
            return

        logger.debug(f"Semantic cache searching for: {context.rendered_prompt[:80]}...")

        results = await self.collection.search(
            context.rendered_prompt,
            vector_property_name="prompt",
            top=1
        )

        async for result in results.results:
            logger.debug(
                f"Cache candidate: score={result.score:.4f}, threshold={self.score_threshold}"
            )

            if result.score is not None and result.score < self.score_threshold:
                logger.info(
                    f"CACHE HIT — id={result.record.id}, score={result.score:.4f}"
                )
                context.function_result = FunctionResult(
                    function=context.function.metadata,
                    value=result.record.result,
                    rendered_prompt=context.rendered_prompt,
                    metadata={RECORD_ID_KEY: result.record.id},
                )
                return

        logger.info("CACHE MISS — no match found.")

    # ----------------------------------------------------------------------
    # AFTER LLM RUNS: Try to WRITE to cache
    # ----------------------------------------------------------------------
    async def on_function_invocation(self, context: FunctionInvocationContext, next):
        await next(context)

        result = context.result

        if result is None:
            logger.debug("No result produced — skipping cache write.")
            return

        # --------- FIX #2: Skip cache hits ----------
        if RECORD_ID_KEY in result.metadata:
            logger.debug("Skipping write — this was a cache hit.")
            return

        # --------- FIX #3: Skip tools ----------
        if context.function.name != "chat_completion":
            logger.debug(f"Skipping cache write — tool call: {context.function.name}")
            return

        # --------- FIX #4: Only cache final strings ----------
        if not isinstance(result.value, str):
            logger.debug("Skipping cache write — not a final assistant message.")
            return

        # --------- FIX #5: Inject prompt if SK didn't produce one ----------
        if not result.rendered_prompt:
            result.rendered_prompt = getattr(context.kernel, "saved_user_prompt", "")

        if not result.rendered_prompt:
            logger.warning("No rendered prompt available — cannot cache.")
            return

        # --------- Write to vector store ----------
        cache_record = CacheRecord(
            prompt=result.rendered_prompt,
            result=result.value,
        )

        await self.collection.ensure_collection_exists()
        await self.collection.upsert(cache_record)

        logger.info(f"CACHE WRITE — stored id={cache_record.id}")
