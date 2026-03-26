"""Task CRUD endpoints."""

import asyncio
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.dependencies import get_db
from backend.database.models import Task, TaskStatus, Step
from backend.graph.workflow import run_task
from backend.models.schemas import (
    PaginatedTasks,
    StepDetail,
    TaskCreate,
    TaskDetail,
    TaskResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Task:
    """Create a new task and start the agent workflow in the background."""
    task = Task(
        description=body.description,
        project_id=body.project_id,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    task_id = str(task.id)
    project_id = str(body.project_id) if body.project_id else None

    background_tasks.add_task(_run_workflow, task_id, body.description, project_id)
    return task


async def _run_workflow(task_id: str, description: str, project_id: str | None) -> None:
    """Execute the LangGraph workflow in the background."""
    try:
        await run_task(description, project_id=project_id, task_id=task_id)
    except Exception as exc:
        logger.error("Background workflow failed for task %s: %s", task_id, exc)


@router.get("", response_model=PaginatedTasks)
async def list_tasks(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List tasks with pagination and optional status filter."""
    query = select(Task).order_by(Task.created_at.desc())
    count_query = select(func.count(Task.id))

    if status:
        try:
            ts = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        query = query.where(Task.status == ts)
        count_query = count_query.where(Task.status == ts)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return {
        "items": tasks,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Task:
    """Get task details including steps and code artifacts."""
    result = await db.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.steps).selectinload(Step.code_artifacts)
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/steps", response_model=list[StepDetail])
async def get_task_steps(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list:
    """List all steps for a task, including code artifacts."""
    result = await db.execute(
        select(Step)
        .where(Step.task_id == task_id)
        .options(selectinload(Step.code_artifacts))
        .order_by(Step.order)
    )
    steps = result.scalars().all()
    if not steps:
        # Verify the task exists
        task_result = await db.execute(select(Task.id).where(Task.id == task_id))
        if not task_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Task not found")
    return steps


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Task:
    """Cancel a running or pending task."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        raise HTTPException(
            status_code=409,
            detail=f"Task is already {task.status.value} and cannot be cancelled",
        )

    task.status = TaskStatus.CANCELLED
    task.result_summary = "Cancelled by user"
    await db.flush()
    await db.refresh(task)
    return task
