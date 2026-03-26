"""Execution agent — runs generated code in a sandboxed subprocess."""

import asyncio
import tempfile
from pathlib import Path

from backend.agents.base_agent import BaseAgent
from backend.graph.state import AgenticState

_MAX_TIMEOUT_SECONDS = 30
_MAX_OUTPUT_LENGTH = 10_000


class ExecutionAgent(BaseAgent):
    """Executes generated code via subprocess and captures results."""

    agent_type = "execution"

    async def run(self, state: AgenticState) -> dict:
        artifacts = state.get("code_artifacts", [])
        idx = state["current_step_index"]
        steps = state["steps"]

        if not artifacts:
            return {
                "execution_success": False,
                "execution_output": "No code artifacts to execute.",
            }

        step = steps[idx] if idx < len(steps) else {"title": "Unknown"}
        self.logger.info("Executing code for step %d: %s", idx + 1, step.get("title", ""))

        all_output: list[str] = []
        success = True

        for artifact in artifacts:
            lang = artifact.get("language", "").lower()
            if lang not in ("python", "py"):
                all_output.append(
                    f"Skipped {artifact['file_path']} (language: {artifact['language']})"
                )
                continue

            result = await self._run_python(artifact["content"], artifact["file_path"])
            all_output.append(result["output"])
            if not result["success"]:
                success = False

        combined_output = "\n\n".join(all_output)[:_MAX_OUTPUT_LENGTH]
        self.logger.info("Execution %s for step %d", "SUCCESS" if success else "FAILED", idx + 1)

        update: dict = {
            "execution_success": success,
            "execution_output": combined_output,
        }

        if success:
            # Advance to next step and reset retries
            update["current_step_index"] = idx + 1
            update["iteration_count"] = 0
        else:
            update["iteration_count"] = state.get("iteration_count", 0) + 1

        return update

    # ── helpers ──────────────────────────────────────────────────

    async def _run_python(self, code: str, file_path: str) -> dict:
        """Run a Python script in a temporary directory with a timeout."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            script_path = Path(tmp_dir) / "script.py"
            script_path.write_text(code, encoding="utf-8")

            try:
                proc = await asyncio.create_subprocess_exec(
                    "python",
                    str(script_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmp_dir,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=_MAX_TIMEOUT_SECONDS
                )

                stdout_text = stdout.decode("utf-8", errors="replace")[:_MAX_OUTPUT_LENGTH]
                stderr_text = stderr.decode("utf-8", errors="replace")[:_MAX_OUTPUT_LENGTH]

                if proc.returncode == 0:
                    return {
                        "success": True,
                        "output": f"[{file_path}] Exit code 0\n{stdout_text}".strip(),
                    }
                return {
                    "success": False,
                    "output": (
                        f"[{file_path}] Exit code {proc.returncode}\n"
                        f"STDOUT:\n{stdout_text}\nSTDERR:\n{stderr_text}"
                    ).strip(),
                }
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
                return {
                    "success": False,
                    "output": f"[{file_path}] Timed out after {_MAX_TIMEOUT_SECONDS}s",
                }
            except Exception as exc:
                return {
                    "success": False,
                    "output": f"[{file_path}] Execution error: {exc}",
                }
