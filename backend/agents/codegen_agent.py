"""Code generation agent — produces code for a single task step."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.base_agent import BaseAgent
from backend.graph.state import AgenticState

CODEGEN_SYSTEM_PROMPT = """\
You are an expert software engineer. Generate clean, production-quality code.

Rules:
- Write complete, runnable code (not pseudocode or snippets).
- Follow best practices for the language being used.
- Include proper error handling where appropriate.
- Add type hints for Python code.
- Follow existing code patterns from the codebase context.
- If the step requires modifying existing code, generate the complete updated file.

Respond with a JSON array of code artifacts. Each artifact has:
- "file_path": relative path for the file
- "content": the complete file content
- "language": programming language (e.g., "python", "typescript")

Example:
[
  {"file_path": "src/auth.py", "content": "import jwt\\n...", "language": "python"}
]

Respond ONLY with the JSON array, no other text."""


class CodegenAgent(BaseAgent):
    """Generates code artifacts for the current task step."""

    agent_type = "codegen"

    async def run(self, state: AgenticState) -> dict:
        steps = state["steps"]
        idx = state["current_step_index"]
        context = state.get("context", "")
        review_feedback = state.get("review_feedback", "")
        execution_output = state.get("execution_output", "")

        if idx >= len(steps):
            return {"status": "completed"}

        step = steps[idx]
        self.logger.info("Generating code for step %d/%d: %s", idx + 1, len(steps), step["title"])

        prompt_parts = [
            f"Task: {state['task_description']}",
            f"\nCurrent Step ({idx + 1}/{len(steps)}): {step['title']}",
            f"Step Description: {step['description']}",
        ]

        if context and context != "No codebase context available.":
            prompt_parts.append(f"\nExisting codebase context:\n{context}")

        # Include prior code artifacts for continuity
        prior_artifacts = state.get("code_artifacts", [])
        if prior_artifacts:
            prompt_parts.append("\nPreviously generated code:")
            for art in prior_artifacts:
                prompt_parts.append(f"\n--- {art['file_path']} ---\n{art['content']}")

        # Feed back review / execution issues for retries
        if review_feedback:
            prompt_parts.append(f"\nReview feedback to address:\n{review_feedback}")

        if execution_output and not state.get("execution_success", True):
            prompt_parts.append(f"\nExecution error to fix:\n{execution_output}")

        response = await self.llm.chat(
            [
                SystemMessage(content=CODEGEN_SYSTEM_PROMPT),
                HumanMessage(content="\n".join(prompt_parts)),
            ],
            max_tokens=4096,
        )

        try:
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                raw = raw.rsplit("```", 1)[0]
            artifacts = json.loads(raw.strip())
            if not isinstance(artifacts, list):
                raise ValueError("Expected a JSON array")
        except (json.JSONDecodeError, ValueError) as exc:
            self.logger.error("Failed to parse codegen output: %s", exc)
            return {
                "errors": [f"Codegen output parsing failed: {exc}"],
                "total_tokens": response.total_tokens,
            }

        code_artifacts = [
            {
                "file_path": a["file_path"],
                "content": a["content"],
                "language": a.get("language", "python"),
            }
            for a in artifacts
        ]

        self.logger.info("Generated %d code artifact(s)", len(code_artifacts))
        return {
            "code_artifacts": code_artifacts,
            "review_passed": False,
            "review_feedback": "",
            "execution_success": False,
            "execution_output": "",
            "total_tokens": response.total_tokens,
        }
