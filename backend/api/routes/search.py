"""Vector search endpoint."""

import logging
import uuid

from fastapi import APIRouter, HTTPException

from backend.models.schemas import SearchRequest, SearchResponse, SearchResultItem
from backend.services.embedding_service import EmbeddingService
from backend.vectordb.retriever import Retriever

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search"])

_embedding_service = EmbeddingService()


@router.post("/search", response_model=SearchResponse)
async def search_codebase(body: SearchRequest) -> dict:
    """Search the indexed codebase using natural language."""
    try:
        retriever = Retriever(
            embedding_service=_embedding_service,
            project_id=uuid.UUID(str(body.project_id)) if body.project_id else None,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="No index found. Please index a codebase first via POST /index",
        )

    results = await retriever.search(query=body.query, top_k=body.top_k)

    items = [
        SearchResultItem(
            file_path=r.file_path,
            start_line=r.start_line,
            end_line=r.end_line,
            code_snippet=r.code_snippet,
            chunk_type=r.chunk_type,
            name=r.name,
            language=r.language,
            similarity_score=r.similarity_score,
        )
        for r in results
    ]

    return {"results": items, "total": len(items)}
