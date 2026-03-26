"""LangGraph workflow — the main agent orchestration state machine."""

import logging
import uuid

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from backend.database.engine import async_session_factory
from backend.database.models import Task, TaskStatus
from backend.graph.nodes import (
    execute_code,
    generate_code,
    plan_task,
    retrieve_context,
    review_code,
)
from backend.graph.state import AgenticState

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3


# ═══════════════════════════════════════════════════════════════════
#  Routing functions (pure — they only inspect state)
# ═══════════════════════════════════════════════════════════════════


def _route_after_plan(state: AgenticState) -> str:
    """Skip code generation when the planner failed or produced no steps."""
    if state.get("status") == "failed" or not state.get("steps"):
        return END
    return "generate_code"


def _route_after_review(state: AgenticState) -> str:
    """After code review, decide whether to execute, retry, or give up."""
    if state.get("review_passed"):
        return "execute_code"

    if state.get("iteration_count", 0) < state.get("max_iterations", MAX_ITERATIONS):
        return "generate_code"

    return END


def _route_after_execute(state: AgenticState) -> str:
    """After execution, decide whether to advance, retry, or stop."""
    if state.get("execution_success"):
        # All steps done?
        if state.get("current_step_index", 0) >= len(state.get("steps", [])):
            return END
        # More steps to process
        return "generate_code"

    if state.get("iteration_count", 0) < state.get("max_iterations", MAX_ITERATIONS):
        return "generate_code"

    return END


# ═══════════════════════════════════════════════════════════════════
#  Graph construction
# ═══════════════════════════════════════════════════════════════════


def build_workflow() -> StateGraph:
    """Construct and return the (uncompiled) LangGraph StateGraph."""
    graph = StateGraph(AgenticState)

    # ── nodes ──────────────────────────────────────────────────
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("plan_task", plan_task)
    graph.add_node("generate_code", generate_code)
    graph.add_node("review_code", review_code)
    graph.add_node("execute_code", execute_code)

    # ── edges (linear portion) ─────────────────────────────────
    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "plan_task")
    graph.add_edge("generate_code", "review_code")

    # ── conditional edges ──────────────────────────────────────
    graph.add_conditional_edges(
        "plan_task",
        _route_after_plan,
        {"generate_code": "generate_code", END: END},
    )
    graph.add_conditional_edges(
        "review_code",
        _route_after_review,
        {"execute_code": "execute_code", "generate_code": "generate_code", END: END},
    )
    graph.add_conditional_edges(
        "execute_code",
        _route_after_execute,
        {"generate_code": "generate_code", END: END},
    )

    return graph


# Pre-compiled workflow ready for invocation
workflow = build_workflow().compile()


# ═══════════════════════════════════════════════════════════════════
#  Public entry point
# ═══════════════════════════════════════════════════════════════════


async def run_task(
    task_description: str,
    project_id: str | None = None,
    task_id: str | None = None,
) -> AgenticState:
    """Run the full agent workflow for a developer task.

    Args:
        task_description: Natural-language task description.
        project_id: Optional project UUID for scoped context retrieval.
        task_id: Optional existing task UUID; a new DB row is created when *None*.

    Returns:
        The final :class:`AgenticState` after workflow completion.
    """
    # Create a task row in the database if not provided
    if task_id is None:
        try:
            async with async_session_factory() as session:
                task = Task(
                    project_id=uuid.UUID(project_id) if project_id else None,
                    description=task_description,
                    status=TaskStatus.PENDING,
                )
                session.add(task)
                await session.commit()
                await session.refresh(task)
                task_id = str(task.id)
        except Exception as exc:
            logger.error("Failed to create task in DB: %s", exc)
            task_id = str(uuid.uuid4())

    initial_state: AgenticState = {
        "task_id": task_id,
        "task_description": task_description,
        "project_id": project_id or "",
        "context": "",
        "steps": [],
        "current_step_index": 0,
        "code_artifacts": [],
        "review_passed": False,
        "review_feedback": "",
        "execution_success": False,
        "execution_output": "",
        "errors": [],
        "total_tokens": 0,
        "iteration_count": 0,
        "max_iterations": MAX_ITERATIONS,
        "status": "pending",
        "result_summary": "",
    }

    logger.info("Starting workflow for task %s: %s", task_id, task_description[:80])

    try:
        final_state = await workflow.ainvoke(initial_state)
    except Exception as exc:
        logger.error("Workflow failed for task %s: %s", task_id, exc)
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Task).where(Task.id == uuid.UUID(task_id))
                )
                task = result.scalar_one_or_none()
                if task:
                    task.status = TaskStatus.FAILED
                    task.result_summary = str(exc)[:2000]
                    await session.commit()
        except Exception:
            pass
        raise

    # Persist final token count and summary
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Task).where(Task.id == uuid.UUID(task_id))
            )
            task = result.scalar_one_or_none()
            if task:
                task.total_tokens = final_state.get("total_tokens", 0)
                if final_state.get("result_summary"):
                    task.result_summary = final_state["result_summary"]
                await session.commit()
    except Exception as exc:
        logger.warning("Failed to update task final state: %s", exc)

    logger.info(
        "Workflow completed for task %s — status: %s",
        task_id,
        final_state.get("status"),
    )
    return final_state
