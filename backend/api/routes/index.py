"""Codebase indexing endpoint."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db
from backend.database.models import Project
from backend.models.schemas import IndexRequest, IndexResponse
from backend.services.embedding_service import EmbeddingService
from backend.vectordb.indexer import Indexer

logger = logging.getLogger(__name__)
router = APIRouter(tags=["index"])

_embedding_service = EmbeddingService()
_indexer = Indexer(embedding_service=_embedding_service)


@router.post("/index", response_model=IndexResponse, status_code=202)
async def index_codebase(
    body: IndexRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger codebase indexing for a directory.

    Creates a project record, then indexes the directory in the background.
    """
    root = Path(body.directory).resolve()
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"Directory not found: {body.directory}")

    # Check for existing project with the same name
    result = await db.execute(
        select(Project).where(Project.name == body.project_name)
    )
    project = result.scalar_one_or_none()

    if project is None:
        project = Project(
            name=body.project_name,
            root_path=str(root),
            description=body.description,
        )
        db.add(project)
        await db.flush()
        await db.refresh(project)

    project_id = project.id

    background_tasks.add_task(_index_background, str(root), project_id)

    return {
        "project_id": project_id,
        "project_name": body.project_name,
        "files_indexed": 0,  # actual count determined asynchronously
        "message": "Indexing started in background",
    }


async def _index_background(root_dir: str, project_id: uuid.UUID) -> None:
    """Run indexing in a background task with its own DB session."""
    try:
        from backend.database.engine import async_session_factory

        async with async_session_factory() as session:
            store = await _indexer.index_directory(
                root_dir, project_id=project_id, db_session=session
            )
            await session.commit()
            logger.info(
                "Background indexing complete for project %s: %d vectors",
                project_id,
                store.size,
            )
    except Exception as exc:
        logger.error("Background indexing failed for project %s: %s", project_id, exc)
