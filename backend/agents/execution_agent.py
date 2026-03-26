"""Execution agent — runs generated code in a sandboxed subprocess."""

import asyncio
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.agents.base_agent import BaseAgent
from backend.database.engine import async_session_factory
from backend.database.models import CodeArtifact as CodeArtifactModel, Step
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

        # Build full codebase: collect all artifacts from all prior completed steps + current step
        all_artifacts: dict[str, str] = {}
        
        # Fetch artifacts from all prior passed steps from DB
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Step)
                    .where(Step.task_id == uuid.UUID(state["task_id"]))
                    .options(selectinload(Step.code_artifacts))
                    .order_by(Step.order)
                )
                db_steps = result.scalars().all()
                
                for db_step in db_steps:
                    if db_step.order >= idx:
                        break
                    for artifact in db_step.code_artifacts:
                        all_artifacts[artifact.file_path] = artifact.content
        except Exception as exc:
            self.logger.warning("Failed to fetch prior step artifacts: %s", exc)
        
        # Add current step artifacts (may override prior versions)
        for artifact in artifacts:
            all_artifacts[artifact["file_path"]] = artifact["content"]

        # Execute test files only; skip non-test artifacts
        test_files = [fp for fp in all_artifacts if "test" in fp.lower() or fp.endswith("_test.py")]
        exec_files = test_files if test_files else list(all_artifacts.keys())
        
        all_output: list[str] = []
        success = True

        for file_path in exec_files:
            lang = file_path.split(".")[-1].lower()
            if lang not in ("py", "python"):
                all_output.append(f"Skipped {file_path} (not Python)")
                continue

            result = await self._run_python_with_codebase(all_artifacts, file_path)
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

    def _run_python_with_codebase_sync(
        self, all_artifacts: dict[str, str], entry_file: str
    ) -> dict:
        """Run a Python script with full codebase structure in temp directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Write all artifacts to temp dir (creates subdirectories as needed)
            for file_path, content in all_artifacts.items():
                full_path = tmp_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
            
            entry_script = tmp_path / entry_file

            try:
                result = subprocess.run(
                    [sys.executable, str(entry_script)],
                    capture_output=True,
                    timeout=_MAX_TIMEOUT_SECONDS,
                    cwd=tmp_dir,
                )

                stdout_text = result.stdout.decode("utf-8", errors="replace")[:_MAX_OUTPUT_LENGTH]
                stderr_text = result.stderr.decode("utf-8", errors="replace")[:_MAX_OUTPUT_LENGTH]

                if result.returncode == 0:
                    return {
                        "success": True,
                        "output": f"[{entry_file}] Exit code 0\n{stdout_text}".strip(),
                    }
                return {
                    "success": False,
                    "output": (
                        f"[{entry_file}] Exit code {result.returncode}\n"
                        f"STDOUT:\n{stdout_text}\nSTDERR:\n{stderr_text}"
                    ).strip(),
                }
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "output": f"[{entry_file}] Timed out after {_MAX_TIMEOUT_SECONDS}s",
                }
            except Exception as exc:
                return {
                    "success": False,
                    "output": f"[{entry_file}] Execution error: {type(exc).__name__}: {exc}",
                }

    async def _run_python_with_codebase(
        self, all_artifacts: dict[str, str], entry_file: str
    ) -> dict:
        """Run a Python script with full codebase (async wrapper)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._run_python_with_codebase_sync, all_artifacts, entry_file
        )

    def _run_python_sync(self, code: str, file_path: str) -> dict:
        """Run a Python script synchronously in a temporary directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            script_path = Path(tmp_dir) / "script.py"
            script_path.write_text(code, encoding="utf-8")

            try:
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    timeout=_MAX_TIMEOUT_SECONDS,
                    cwd=tmp_dir,
                )

                stdout_text = result.stdout.decode("utf-8", errors="replace")[:_MAX_OUTPUT_LENGTH]
                stderr_text = result.stderr.decode("utf-8", errors="replace")[:_MAX_OUTPUT_LENGTH]

                if result.returncode == 0:
                    return {
                        "success": True,
                        "output": f"[{file_path}] Exit code 0\n{stdout_text}".strip(),
                    }
                return {
                    "success": False,
                    "output": (
                        f"[{file_path}] Exit code {result.returncode}\n"
                        f"STDOUT:\n{stdout_text}\nSTDERR:\n{stderr_text}"
                    ).strip(),
                }
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "output": f"[{file_path}] Timed out after {_MAX_TIMEOUT_SECONDS}s",
                }
            except Exception as exc:
                return {
                    "success": False,
                    "output": f"[{file_path}] Execution error: {type(exc).__name__}: {exc}",
                }

    async def _run_python(self, code: str, file_path: str) -> dict:
        """Run a Python script in a temporary directory with a timeout."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._run_python_sync, code, file_path
        )
