"""LangGraph node functions — wrap agents and persist to PostgreSQL."""

import logging
import time
import uuid

from sqlalchemy import select

from backend.agents.codegen_agent import CodegenAgent
from backend.agents.context_agent import ContextAgent
from backend.agents.execution_agent import ExecutionAgent
from backend.agents.planner_agent import PlannerAgent
from backend.agents.review_agent import ReviewAgent
from backend.database.engine import async_session_factory
from backend.database.models import (
    AgentLog,
    AgentType,
    CodeArtifact as CodeArtifactModel,
    Step,
    StepStatus,
    Task,
    TaskStatus,
)
from backend.graph.state import AgenticState
from backend.services.cache_service import CacheService
from backend.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ── Shared service instances (created once, reused across nodes) ──
_llm_client = LLMClient()
_cache_service = CacheService()

_context_agent = ContextAgent(llm_client=_llm_client, cache_service=_cache_service)
_planner_agent = PlannerAgent(llm_client=_llm_client, cache_service=_cache_service)
_codegen_agent = CodegenAgent(llm_client=_llm_client, cache_service=_cache_service)
_review_agent = ReviewAgent(llm_client=_llm_client, cache_service=_cache_service)
_execution_agent = ExecutionAgent(llm_client=_llm_client, cache_service=_cache_service)


# ═══════════════════════════════════════════════════════════════════
#  DB helper utilities
# ═══════════════════════════════════════════════════════════════════


async def _log_agent(
    task_id: str,
    step_id: str | None,
    agent_type: AgentType,
    input_text: str,
    output_text: str,
    tokens_used: int,
    duration_ms: int,
    error: str | None = None,
) -> None:
    """Persist an agent log row."""
    try:
        async with async_session_factory() as session:
            log = AgentLog(
                task_id=uuid.UUID(task_id),
                step_id=uuid.UUID(step_id) if step_id else None,
                agent_type=agent_type,
                input_text=(input_text or "")[:5000],
                output_text=(output_text or "")[:5000],
                tokens_used=tokens_used,
                duration_ms=duration_ms,
                error=error,
            )
            session.add(log)
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to persist agent log: %s", exc)


async def _update_task_status(task_id: str, status: TaskStatus) -> None:
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Task).where(Task.id == uuid.UUID(task_id))
            )
            task = result.scalar_one_or_none()
            if task:
                task.status = status
                await session.commit()
    except Exception as exc:
        logger.warning("Failed to update task status: %s", exc)


async def _get_step_id(task_id: str, step_order: int) -> str | None:
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Step).where(
                    Step.task_id == uuid.UUID(task_id),
                    Step.order == step_order,
                )
            )
            step = result.scalar_one_or_none()
            return str(step.id) if step else None
    except Exception:
        return None


async def _update_step_status(
    task_id: str,
    step_order: int,
    status: StepStatus,
    increment_retry: bool = False,
) -> None:
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Step).where(
                    Step.task_id == uuid.UUID(task_id),
                    Step.order == step_order,
                )
            )
            step = result.scalar_one_or_none()
            if step:
                step.status = status
                if increment_retry:
                    step.retry_count += 1
                await session.commit()
    except Exception as exc:
        logger.warning("Failed to update step status: %s", exc)


async def _persist_artifacts(step_id: str, artifacts: list[dict]) -> None:
    try:
        async with async_session_factory() as session:
            for art in artifacts:
                ca = CodeArtifactModel(
                    step_id=uuid.UUID(step_id),
                    file_path=art["file_path"],
                    content=art["content"],
                    language=art.get("language"),
                )
                session.add(ca)
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to persist code artifacts: %s", exc)


# ═══════════════════════════════════════════════════════════════════
#  LangGraph node functions
# ═══════════════════════════════════════════════════════════════════


async def retrieve_context(state: AgenticState) -> dict:
    """Node: retrieve relevant code context from FAISS."""
    start = time.perf_counter()
    await _update_task_status(state["task_id"], TaskStatus.PLANNING)

    result = await _context_agent.run(state)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    await _log_agent(
        task_id=state["task_id"],
        step_id=None,
        agent_type=AgentType.CONTEXT,
        input_text=state["task_description"],
        output_text=(result.get("context") or "")[:500],
        tokens_used=result.get("total_tokens", 0),
        duration_ms=elapsed_ms,
    )
    return result


async def plan_task(state: AgenticState) -> dict:
    """Node: decompose the task into ordered steps."""
    start = time.perf_counter()
    result = await _planner_agent.run(state)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    # Persist steps to the database
    steps = result.get("steps", [])
    if steps:
        try:
            async with async_session_factory() as session:
                for i, step_plan in enumerate(steps):
                    session.add(
                        Step(
                            task_id=uuid.UUID(state["task_id"]),
                            order=i,
                            title=step_plan["title"],
                            description=step_plan["description"],
                        )
                    )
                await session.commit()
        except Exception as exc:
            logger.warning("Failed to persist steps: %s", exc)

        await _update_task_status(state["task_id"], TaskStatus.IN_PROGRESS)

    await _log_agent(
        task_id=state["task_id"],
        step_id=None,
        agent_type=AgentType.PLANNER,
        input_text=state["task_description"],
        output_text=str(steps)[:2000],
        tokens_used=result.get("total_tokens", 0),
        duration_ms=elapsed_ms,
    )
    return result


async def generate_code(state: AgenticState) -> dict:
    """Node: generate code for the current step."""
    start = time.perf_counter()
    idx = state["current_step_index"]
    await _update_step_status(state["task_id"], idx, StepStatus.GENERATING)

    result = await _codegen_agent.run(state)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    step_id = await _get_step_id(state["task_id"], idx)
    await _log_agent(
        task_id=state["task_id"],
        step_id=step_id,
        agent_type=AgentType.CODEGEN,
        input_text=state["steps"][idx]["description"] if idx < len(state["steps"]) else "",
        output_text=str(result.get("code_artifacts", []))[:2000],
        tokens_used=result.get("total_tokens", 0),
        duration_ms=elapsed_ms,
    )
    return result


async def review_code(state: AgenticState) -> dict:
    """Node: review generated code for quality and security."""
    start = time.perf_counter()
    idx = state["current_step_index"]
    await _update_step_status(state["task_id"], idx, StepStatus.REVIEWING)

    result = await _review_agent.run(state)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    step_id = await _get_step_id(state["task_id"], idx)
    await _log_agent(
        task_id=state["task_id"],
        step_id=step_id,
        agent_type=AgentType.REVIEW,
        input_text="Code review",
        output_text=result.get("review_feedback", ""),
        tokens_used=result.get("total_tokens", 0),
        duration_ms=elapsed_ms,
    )

    # Increment DB retry count when review fails
    if not result.get("review_passed"):
        await _update_step_status(
            state["task_id"], idx, StepStatus.REVIEWING, increment_retry=True
        )

    return result


async def execute_code(state: AgenticState) -> dict:
    """Node: execute/test the generated code."""
    start = time.perf_counter()
    idx = state["current_step_index"]
    await _update_step_status(state["task_id"], idx, StepStatus.EXECUTING)

    result = await _execution_agent.run(state)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    step_id = await _get_step_id(state["task_id"], idx)
    await _log_agent(
        task_id=state["task_id"],
        step_id=step_id,
        agent_type=AgentType.EXECUTION,
        input_text="Code execution",
        output_text=result.get("execution_output", ""),
        tokens_used=0,
        duration_ms=elapsed_ms,
    )

    if result.get("execution_success"):
        await _update_step_status(state["task_id"], idx, StepStatus.PASSED)

        # Persist code artifacts to DB
        artifacts = state.get("code_artifacts", [])
        if artifacts and step_id:
            await _persist_artifacts(step_id, artifacts)

        # Check whether all steps are done
        if idx + 1 >= len(state["steps"]):
            await _update_task_status(state["task_id"], TaskStatus.COMPLETED)
            result["status"] = "completed"
            result["result_summary"] = (
                f"Completed all {len(state['steps'])} steps successfully."
            )
    else:
        # On failure with max retries exhausted, mark step as failed
        if result.get("iteration_count", 0) >= state.get("max_iterations", 3):
            await _update_step_status(
                state["task_id"], idx, StepStatus.FAILED, increment_retry=True
            )
            await _update_task_status(state["task_id"], TaskStatus.FAILED)
            result["status"] = "failed"
            result["errors"] = [
                f"Step {idx + 1} failed after max retries: "
                + result.get("execution_output", "")[:500]
            ]

    return result
