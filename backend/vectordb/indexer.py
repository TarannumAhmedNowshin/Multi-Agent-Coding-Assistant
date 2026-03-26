"""Codebase indexer — walks a directory, parses files, and builds a FAISS index."""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database.models import Project
from backend.services.embedding_service import EmbeddingService
from backend.utils.file_parser import SUPPORTED_EXTENSIONS, CodeChunk, parse_file
from backend.utils.text_splitter import TextSplitter
from backend.vectordb.faiss_store import ChunkMetadata, FAISSStore

logger = logging.getLogger(__name__)

# Directories to skip when walking a codebase
_SKIP_DIRS: set[str] = {
    ".git", ".svn", ".hg",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "node_modules", ".next", "dist", "build",
    ".venv", "venv", "env",
    ".tox", ".nox",
    ".idea", ".vscode",
    "egg-info",
}

# Maximum single-file size to index (1 MB)
_MAX_FILE_BYTES = 1_048_576


def _should_skip_dir(name: str) -> bool:
    """Return True if a directory should be skipped."""
    lower = name.lower()
    return lower in _SKIP_DIRS or lower.endswith(".egg-info")


def _collect_files(root: Path) -> list[Path]:
    """Recursively collect indexable source files under *root*."""
    files: list[Path] = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            if _should_skip_dir(entry.name):
                continue
            files.extend(_collect_files(entry))
        elif entry.is_file():
            if (
                entry.suffix.lower() in SUPPORTED_EXTENSIONS
                and entry.stat().st_size <= _MAX_FILE_BYTES
            ):
                files.append(entry)
    return files


class Indexer:
    """Index a codebase directory into a FAISS vector store."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        text_splitter: TextSplitter | None = None,
    ) -> None:
        self._embed = embedding_service or EmbeddingService()
        self._splitter = text_splitter or TextSplitter()

    def _index_dir(self) -> Path:
        """Default directory to persist FAISS indexes."""
        return Path(".index_store")

    def _project_index_dir(self, project_id: uuid.UUID) -> Path:
        return self._index_dir() / str(project_id)

    async def index_directory(
        self,
        root_dir: str | Path,
        project_id: uuid.UUID | None = None,
        db_session: AsyncSession | None = None,
    ) -> FAISSStore:
        """Walk *root_dir*, parse, embed, and store in FAISS.

        Args:
            root_dir: Directory to index.
            project_id: Optional project UUID; if provided the FAISS index
                is saved under ``.index_store/<project_id>/`` and the
                project's ``indexed_at`` is updated.
            db_session: Optional async DB session (needed to update project).

        Returns:
            The populated FAISSStore instance.
        """
        root = Path(root_dir).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Directory not found: {root}")

        logger.info("Indexing directory: %s", root)

        # 1. Collect files
        files = _collect_files(root)
        logger.info("Found %d indexable files", len(files))

        if not files:
            store = FAISSStore(dimensions=self._embed.dimensions)
            store.create_index()
            return store

        # 2. Parse into chunks
        all_chunks: list[CodeChunk] = []
        for file_path in files:
            try:
                chunks = parse_file(str(file_path))
                all_chunks.extend(chunks)
            except Exception:
                logger.warning("Failed to parse %s — skipping", file_path, exc_info=True)

        logger.info("Parsed %d code chunks from %d files", len(all_chunks), len(files))

        # 3. Split oversized chunks
        all_chunks = self._splitter.split_chunks(all_chunks)
        logger.info("After splitting: %d chunks", len(all_chunks))

        if not all_chunks:
            store = FAISSStore(dimensions=self._embed.dimensions)
            store.create_index()
            return store

        # 4. Generate embeddings
        texts = [
            f"{c.chunk_type} {c.name}\n{c.content}" for c in all_chunks
        ]
        embed_result = await self._embed.embed_texts(texts)
        logger.info(
            "Generated %d embeddings (%d tokens)",
            embed_result.vectors.shape[0],
            embed_result.total_tokens,
        )

        # 5. Build FAISS index
        store = FAISSStore(dimensions=self._embed.dimensions)
        store.create_index()

        metadata_list = [
            ChunkMetadata(
                file_path=c.file_path,
                start_line=c.start_line,
                end_line=c.end_line,
                chunk_type=c.chunk_type,
                name=c.name,
                content=c.content,
                language=c.language,
            )
            for c in all_chunks
        ]
        store.add_vectors(embed_result.vectors, metadata_list)

        # 6. Persist to disk
        if project_id is not None:
            save_dir = self._project_index_dir(project_id)
        else:
            save_dir = self._index_dir() / "default"
        store.save(save_dir)

        # 7. Update project.indexed_at
        if project_id is not None and db_session is not None:
            result = await db_session.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            if project is not None:
                project.indexed_at = datetime.now(timezone.utc)
                await db_session.flush()
                logger.info("Updated project %s indexed_at", project_id)

        logger.info("Indexing complete: %d vectors in store", store.size)
        return store

    def load_index(self, project_id: uuid.UUID | None = None) -> FAISSStore:
        """Load a previously saved FAISS index from disk.

        Args:
            project_id: If provided, loads ``.index_store/<project_id>/``;
                otherwise loads ``.index_store/default/``.

        Returns:
            The loaded FAISSStore.
        """
        if project_id is not None:
            load_dir = self._project_index_dir(project_id)
        else:
            load_dir = self._index_dir() / "default"

        store = FAISSStore(dimensions=self._embed.dimensions)
        store.load(load_dir)
        return store
