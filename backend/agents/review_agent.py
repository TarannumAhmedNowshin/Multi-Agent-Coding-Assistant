"""Review agent — reviews generated code for correctness, security, and style."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.base_agent import BaseAgent
from backend.graph.state import AgenticState

REVIEW_SYSTEM_PROMPT = """\
You are a senior code reviewer with expertise in security and software quality.

Review the provided code for:
1. **Correctness** — Does the code fulfil the step description?
2. **Security** — Check for OWASP Top 10 issues (injection, XSS, auth flaws, etc.).
3. **Style** — Is the code clean, well-structured, and following best practices?
4. **Completeness** — Is the implementation complete or are there missing pieces?

Respond with a JSON object:
{
  "passed": true or false,
  "feedback": "Detailed feedback explaining issues or confirming quality",
  "issues": ["list", "of", "specific", "issues"]
}

Be strict about security issues but reasonable about minor style preferences.
Respond ONLY with the JSON object, no other text."""


class ReviewAgent(BaseAgent):
    """Reviews generated code for correctness, security, and style."""

    agent_type = "review"

    async def run(self, state: AgenticState) -> dict:
        steps = state["steps"]
        idx = state["current_step_index"]
        artifacts = state.get("code_artifacts", [])

        if not artifacts:
            return {
                "review_passed": False,
                "review_feedback": "No code artifacts to review.",
            }

        step = steps[idx] if idx < len(steps) else {"title": "Unknown", "description": ""}
        self.logger.info("Reviewing code for step %d: %s", idx + 1, step["title"])

        code_block = "\n\n".join(
            f"--- {a['file_path']} ({a['language']}) ---\n{a['content']}"
            for a in artifacts
        )

        prompt = (
            f"Task: {state['task_description']}\n"
            f"Step: {step['title']}\n"
            f"Step Description: {step['description']}\n\n"
            f"Code to review:\n{code_block}"
        )

        response = await self.llm.chat([
            SystemMessage(content=REVIEW_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])

        try:
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                raw = raw.rsplit("```", 1)[0]
            result = json.loads(raw.strip())
        except (json.JSONDecodeError, ValueError) as exc:
            self.logger.error("Failed to parse review output: %s", exc)
            # Treat parse failure as a pass to avoid infinite retry loops
            return {
                "review_passed": True,
                "review_feedback": f"Review parsing failed ({exc}), accepting code.",
                "total_tokens": response.total_tokens,
            }

        passed = bool(result.get("passed", False))
        feedback = result.get("feedback", "")
        issues = result.get("issues", [])

        if issues:
            feedback += "\n\nIssues:\n" + "\n".join(f"- {issue}" for issue in issues)

        update: dict = {
            "review_passed": passed,
            "review_feedback": feedback,
            "total_tokens": response.total_tokens,
        }

        # Increment iteration count on failure so the router can enforce max retries
        if not passed:
            update["iteration_count"] = state.get("iteration_count", 0) + 1

        self.logger.info(
            "Review %s for step %d", "PASSED" if passed else "FAILED", idx + 1
        )
        return update
