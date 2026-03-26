"""Azure OpenAI embedding service with batching and token-aware chunking."""

import logging
from dataclasses import dataclass

import numpy as np
import tiktoken
from langchain_openai import AzureOpenAIEmbeddings

from backend.config import settings

logger = logging.getLogger(__name__)

# text-embedding-3-small has a max input of 8191 tokens
_MAX_TOKENS_PER_INPUT = 8191
_BATCH_SIZE = 16  # Azure OpenAI batch limit


@dataclass
class EmbeddingResult:
    """Result of an embedding request."""

    vectors: np.ndarray  # shape (n, dimensions)
    total_tokens: int


class EmbeddingService:
    """Generate embeddings via Azure OpenAI text-embedding-3-small."""

    def __init__(self) -> None:
        self._model = AzureOpenAIEmbeddings(
            azure_endpoint=settings.embed_endpoint,
            api_key=settings.embed_api_key,
            api_version=settings.embed_api_version,
            azure_deployment=settings.embed_deployment,
            model=settings.embed_model,
            dimensions=settings.embed_dimensions,
        )
        self._tokenizer = tiktoken.get_encoding("cl100k_base")
        self.dimensions = settings.embed_dimensions

    def _truncate_text(self, text: str) -> str:
        """Truncate text to fit within the model's token limit."""
        tokens = self._tokenizer.encode(text)
        if len(tokens) <= _MAX_TOKENS_PER_INPUT:
            return text
        return self._tokenizer.decode(tokens[:_MAX_TOKENS_PER_INPUT])

    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        """Embed a list of texts, batching as needed.

        Returns numpy array of shape (len(texts), dimensions).
        """
        if not texts:
            return EmbeddingResult(
                vectors=np.empty((0, self.dimensions), dtype=np.float32),
                total_tokens=0,
            )

        truncated = [self._truncate_text(t) for t in texts]
        all_vectors: list[list[float]] = []
        total_tokens = 0

        for i in range(0, len(truncated), _BATCH_SIZE):
            batch = truncated[i : i + _BATCH_SIZE]
            vectors = await self._model.aembed_documents(batch)
            all_vectors.extend(vectors)

            # Estimate token usage
            for text in batch:
                total_tokens += len(self._tokenizer.encode(text))

        arr = np.array(all_vectors, dtype=np.float32)
        logger.info("Embedded %d texts (%d tokens)", len(texts), total_tokens)
        return EmbeddingResult(vectors=arr, total_tokens=total_tokens)

    async def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string. Returns 1-D array of shape (dimensions,)."""
        truncated = self._truncate_text(query)
        vector = await self._model.aembed_query(truncated)
        return np.array(vector, dtype=np.float32)

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        return len(self._tokenizer.encode(text))
