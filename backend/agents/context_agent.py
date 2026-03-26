"""Context retrieval agent — fetches relevant code from the FAISS index."""

import uuid

from backend.agents.base_agent import BaseAgent
from backend.graph.state import AgenticState
from backend.vectordb.retriever import Retriever


class ContextAgent(BaseAgent):
    """Retrieves relevant code context from the FAISS vector store."""

    agent_type = "context"

    async def run(self, state: AgenticState) -> dict:
        project_id = state.get("project_id")
        task_desc = state["task_description"]

        self.logger.info("Retrieving context for: %s", task_desc[:80])

        try:
            pid = uuid.UUID(project_id) if project_id else None
            retriever = Retriever(project_id=pid)
            results = await retriever.search(task_desc, top_k=10)
            context = retriever.format_context(results)
        except FileNotFoundError:
            self.logger.warning("No FAISS index found — proceeding without context")
            context = "No codebase context available."
        except Exception as exc:
            self.logger.error("Context retrieval failed: %s", exc)
            context = "No codebase context available."

        self.logger.info("Retrieved context (%d chars)", len(context))
        return {"context": context}
