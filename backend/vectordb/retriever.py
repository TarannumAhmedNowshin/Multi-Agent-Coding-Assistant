"""RAG retriever — query a FAISS index with natural language."""

import logging
import uuid
from dataclasses import dataclass

from backend.services.embedding_service import EmbeddingService
from backend.vectordb.faiss_store import FAISSStore, SearchResult
from backend.vectordb.indexer import Indexer

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A code snippet returned by the retriever."""

    file_path: str
    start_line: int
    end_line: int
    code_snippet: str
    chunk_type: str
    name: str
    language: str
    similarity_score: float


class Retriever:
    """Query interface for codebase vector search."""

    def __init__(
        self,
        store: FAISSStore | None = None,
        embedding_service: EmbeddingService | None = None,
        project_id: uuid.UUID | None = None,
    ) -> None:
        self._embed = embedding_service or EmbeddingService()

        if store is not None:
            self._store = store
        else:
            # Load from disk
            indexer = Indexer(embedding_service=self._embed)
            self._store = indexer.load_index(project_id)

    @property
    def store(self) -> FAISSStore:
        return self._store

    async def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        """Search the index with a natural language query.

        Args:
            query: Natural language question (e.g. "authentication functions").
            top_k: Maximum number of results.
            min_score: Minimum similarity score threshold (0-1).

        Returns:
            List of RetrievalResult sorted by descending similarity.
        """
        query_vector = await self._embed.embed_query(query)
        raw_results: list[SearchResult] = self._store.search(query_vector, top_k=top_k)

        results: list[RetrievalResult] = []
        for r in raw_results:
            if r.similarity_score < min_score:
                continue
            results.append(RetrievalResult(
                file_path=r.file_path,
                start_line=r.start_line,
                end_line=r.end_line,
                code_snippet=r.content,
                chunk_type=r.chunk_type,
                name=r.name,
                language=r.language,
                similarity_score=r.similarity_score,
            ))

        logger.info(
            "Query '%s' returned %d results (top_k=%d, min_score=%.2f)",
            query[:80],
            len(results),
            top_k,
            min_score,
        )
        return results

    def format_context(self, results: list[RetrievalResult]) -> str:
        """Format retrieval results into a context string for LLM prompts.

        Produces a block like:
            ## File: src/auth.py (lines 10-35) [function: login]
            ```python
            def login(...): ...
            ```
        """
        if not results:
            return "No relevant code context found."

        sections: list[str] = []
        for r in results:
            header = (
                f"## File: {r.file_path} (lines {r.start_line}-{r.end_line}) "
                f"[{r.chunk_type}: {r.name}]"
            )
            code_block = f"```{r.language}\n{r.code_snippet}\n```"
            sections.append(f"{header}\n{code_block}")

        return "\n\n".join(sections)
