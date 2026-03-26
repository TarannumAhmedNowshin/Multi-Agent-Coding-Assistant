"""FAISS vector index wrapper with metadata persistence."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result from the FAISS index."""

    chunk_id: int
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str
    name: str
    content: str
    language: str
    similarity_score: float


@dataclass
class ChunkMetadata:
    """Metadata stored alongside each vector in the index."""

    file_path: str
    start_line: int
    end_line: int
    chunk_type: str
    name: str
    content: str
    language: str


class FAISSStore:
    """Wrapper around a FAISS flat-L2 index with JSON metadata sidecar."""

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions
        self._index: faiss.IndexFlatL2 | None = None
        self._metadata: list[ChunkMetadata] = []

    # ── Index lifecycle ───────────────────────────────────────────

    def create_index(self) -> None:
        """Create a fresh empty FAISS index."""
        self._index = faiss.IndexFlatL2(self.dimensions)
        self._metadata = []
        logger.info("Created new FAISS index (dim=%d)", self.dimensions)

    @property
    def index(self) -> faiss.IndexFlatL2:
        if self._index is None:
            raise RuntimeError("Index not initialised. Call create_index() or load().")
        return self._index

    @property
    def size(self) -> int:
        """Number of vectors currently in the index."""
        return self.index.ntotal

    # ── Add vectors ───────────────────────────────────────────────

    def add_vectors(
        self,
        vectors: np.ndarray,
        metadata_list: list[ChunkMetadata],
    ) -> None:
        """Add vectors and their metadata to the index.

        Args:
            vectors: ndarray of shape (n, dimensions), dtype float32.
            metadata_list: one ChunkMetadata per vector.
        """
        if vectors.shape[0] != len(metadata_list):
            raise ValueError(
                f"vectors ({vectors.shape[0]}) and metadata ({len(metadata_list)}) "
                "must have the same length"
            )
        if vectors.shape[1] != self.dimensions:
            raise ValueError(
                f"Vector dimension {vectors.shape[1]} != index dimension {self.dimensions}"
            )

        self.index.add(vectors)
        self._metadata.extend(metadata_list)
        logger.info("Added %d vectors (total: %d)", vectors.shape[0], self.size)

    # ── Search ────────────────────────────────────────────────────

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Find the top_k most similar vectors.

        Args:
            query_vector: 1-D array of shape (dimensions,).
            top_k: number of results to return.

        Returns:
            List of SearchResult ordered by ascending distance (best first).
        """
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        k = min(top_k, self.size)
        if k == 0:
            return []

        distances, indices = self.index.search(query_vector, k)

        results: list[SearchResult] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            meta = self._metadata[idx]
            # Convert L2 distance to a 0-1 similarity score
            similarity = 1.0 / (1.0 + float(dist))
            results.append(SearchResult(
                chunk_id=int(idx),
                file_path=meta.file_path,
                start_line=meta.start_line,
                end_line=meta.end_line,
                chunk_type=meta.chunk_type,
                name=meta.name,
                content=meta.content,
                language=meta.language,
                similarity_score=similarity,
            ))

        return results

    # ── Persistence ───────────────────────────────────────────────

    def save(self, directory: str | Path) -> None:
        """Save the FAISS index and metadata to disk.

        Creates two files: ``faiss.index`` and ``faiss_metadata.json``.
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        index_path = directory / "faiss.index"
        meta_path = directory / "faiss_metadata.json"

        faiss.write_index(self.index, str(index_path))

        serialised = [
            {
                "file_path": m.file_path,
                "start_line": m.start_line,
                "end_line": m.end_line,
                "chunk_type": m.chunk_type,
                "name": m.name,
                "content": m.content,
                "language": m.language,
            }
            for m in self._metadata
        ]
        meta_path.write_text(json.dumps(serialised, indent=2), encoding="utf-8")

        logger.info(
            "Saved FAISS index (%d vectors) to %s", self.size, directory
        )

    def load(self, directory: str | Path) -> None:
        """Load a previously saved FAISS index and metadata from disk."""
        directory = Path(directory)
        index_path = directory / "faiss.index"
        meta_path = directory / "faiss_metadata.json"

        if not index_path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                f"FAISS index files not found in {directory}"
            )

        self._index = faiss.read_index(str(index_path))
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
        self._metadata = [
            ChunkMetadata(
                file_path=item["file_path"],
                start_line=item["start_line"],
                end_line=item["end_line"],
                chunk_type=item["chunk_type"],
                name=item["name"],
                content=item["content"],
                language=item["language"],
            )
            for item in raw
        ]

        if self._index.d != self.dimensions:
            raise ValueError(
                f"Loaded index dimension {self._index.d} != expected {self.dimensions}"
            )

        logger.info(
            "Loaded FAISS index (%d vectors) from %s", self.size, directory
        )
