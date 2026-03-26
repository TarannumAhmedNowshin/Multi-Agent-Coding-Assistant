"""Base agent class for all LangGraph agents."""

import logging
from abc import ABC, abstractmethod

from backend.graph.state import AgenticState
from backend.services.cache_service import CacheService
from backend.services.llm_client import LLMClient


class BaseAgent(ABC):
    """Abstract base for every agent in the workflow.

    Subclasses must set ``agent_type`` and implement ``run()``.
    """

    agent_type: str = "base"

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        cache_service: CacheService | None = None,
    ) -> None:
        self.llm = llm_client or LLMClient()
        self.cache = cache_service
        self.logger = logging.getLogger(f"agent.{self.agent_type}")

    @abstractmethod
    async def run(self, state: AgenticState) -> dict:
        """Execute agent logic and return a **partial** state update dict."""
        ...
