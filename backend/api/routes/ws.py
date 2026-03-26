"""WebSocket endpoint for real-time task progress streaming."""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.database.engine import async_session_factory
from backend.database.models import Step, Task

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_ws(websocket: WebSocket, task_id: str) -> None:
    """Stream task progress updates to the client via WebSocket.

    Polls the database periodically and pushes status changes.
    """
    await websocket.accept()

    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        await websocket.send_json({"event": "error", "data": {"message": "Invalid task ID"}})
        await websocket.close(code=1008)
        return

    last_status: str | None = None
    last_step_statuses: dict[int, str] = {}

    try:
        while True:
            try:
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(Task)
                        .where(Task.id == task_uuid)
                        .options(selectinload(Task.steps))
                    )
                    task = result.scalar_one_or_none()

                if task is None:
                    await websocket.send_json(
                        {"event": "error", "data": {"message": "Task not found"}}
                    )
                    break

                current_status = task.status.value

                # Send task-level status changes
                if current_status != last_status:
                    await websocket.send_json({
                        "event": "task_status",
                        "data": {
                            "task_id": str(task.id),
                            "status": current_status,
                            "total_tokens": task.total_tokens,
                            "result_summary": task.result_summary,
                        },
                    })
                    last_status = current_status

                # Send step-level status changes
                for step in sorted(task.steps, key=lambda s: s.order):
                    step_status = step.status.value
                    if last_step_statuses.get(step.order) != step_status:
                        await websocket.send_json({
                            "event": "step_status",
                            "data": {
                                "step_order": step.order,
                                "title": step.title,
                                "status": step_status,
                                "retry_count": step.retry_count,
                            },
                        })
                        last_step_statuses[step.order] = step_status

                # Terminal states — send final message and close
                if current_status in ("completed", "failed", "cancelled"):
                    await websocket.send_json({
                        "event": "done",
                        "data": {
                            "task_id": str(task.id),
                            "final_status": current_status,
                            "result_summary": task.result_summary,
                        },
                    })
                    break

            except Exception as exc:
                logger.warning("WebSocket poll error: %s", exc)

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for task %s", task_id)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
