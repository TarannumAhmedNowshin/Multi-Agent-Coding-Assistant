"""LangGraph state definition for the agentic workflow."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class StepPlan(TypedDict):
    """A single step in a task plan."""

    title: str
    description: str


class CodeArtifactState(TypedDict):
    """A generated code artifact."""

    file_path: str
    content: str
    language: str


class AgenticState(TypedDict):
    """Shared state passed through the LangGraph workflow.

    Fields annotated with ``operator.add`` are *reducers* — LangGraph
    accumulates values returned by successive nodes instead of replacing them.
    """

    # ── Task info ──
    task_id: str
    task_description: str
    project_id: str

    # ── RAG context ──
    context: str

    # ── Planning ──
    steps: list[StepPlan]
    current_step_index: int

    # ── Code generation ──
    code_artifacts: list[CodeArtifactState]

    # ── Review ──
    review_passed: bool
    review_feedback: str

    # ── Execution ──
    execution_success: bool
    execution_output: str

    # ── Tracking (reducers — values are accumulated across nodes) ──
    errors: Annotated[list[str], operator.add]
    total_tokens: Annotated[int, operator.add]

    # ── Retry control ──
    iteration_count: int
    max_iterations: int

    # ── Final status ──
    status: str
    result_summary: str
