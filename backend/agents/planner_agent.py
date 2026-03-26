"""Planner agent — decomposes a task into ordered implementation steps."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.base_agent import BaseAgent
from backend.graph.state import AgenticState

PLANNER_SYSTEM_PROMPT = """\
You are an expert software architect and project planner.
Your job is to decompose a development task into clear, ordered implementation steps.

Rules:
- Each step should be a single, focused unit of work.
- Steps must be in dependency order (earlier steps do not depend on later ones).
- Each step must have a clear title and a detailed description.
- Include necessary setup, implementation, and testing in the steps.
- Aim for 2-6 steps depending on task complexity.
- Be specific about what code changes each step requires.

Respond with a JSON array of objects, each with "title" and "description" fields.
Example:
[
  {"title": "Create user model", "description": "Define a User SQLAlchemy model with id, email, password_hash, and created_at fields in models.py"},
  {"title": "Add authentication endpoint", "description": "Create POST /auth/login endpoint that validates credentials and returns a JWT token"}
]

Respond ONLY with the JSON array, no other text."""


class PlannerAgent(BaseAgent):
    """Breaks a task into ordered implementation steps via LLM."""

    agent_type = "planner"

    async def run(self, state: AgenticState) -> dict:
        task_desc = state["task_description"]
        context = state.get("context", "")

        prompt = f"Task: {task_desc}"
        if context and context != "No codebase context available.":
            prompt += f"\n\nExisting codebase context:\n{context}"

        self.logger.info("Planning task: %s", task_desc[:80])

        response = await self.llm.chat([
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])

        # Parse the JSON response
        try:
            raw = response.content.strip()
            # Strip optional markdown fencing
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                raw = raw.rsplit("```", 1)[0]
            steps = json.loads(raw.strip())
            if not isinstance(steps, list) or not steps:
                raise ValueError("Expected a non-empty JSON array")
            for step in steps:
                if "title" not in step or "description" not in step:
                    raise ValueError("Each step needs 'title' and 'description'")
        except (json.JSONDecodeError, ValueError) as exc:
            self.logger.error("Failed to parse planner output: %s", exc)
            return {
                "errors": [f"Planner output parsing failed: {exc}"],
                "status": "failed",
                "total_tokens": response.total_tokens,
            }

        self.logger.info("Planned %d steps", len(steps))
        return {
            "steps": [
                {"title": s["title"], "description": s["description"]}
                for s in steps
            ],
            "current_step_index": 0,
            "status": "in_progress",
            "total_tokens": response.total_tokens,
        }
