"""Azure OpenAI LLM client wrapper with retry logic and token tracking."""

import time
from dataclasses import dataclass

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.config import settings


@dataclass
class LLMResponse:
    """Structured response from the LLM."""
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: int


class LLMClient:
    """Wrapper around Azure OpenAI providing chat completions with retries."""

    def __init__(self) -> None:
        self.llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_deployment,
            model=settings.azure_openai_model,
            temperature=0.2,
            max_tokens=4096,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def chat(
        self,
        messages: list[BaseMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Send messages to Azure OpenAI and return a structured response."""
        kwargs: dict = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        start = time.perf_counter()
        response = await self.llm.ainvoke(messages, **kwargs)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        usage = response.usage_metadata or {}
        return LLMResponse(
            content=response.content,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            duration_ms=elapsed_ms,
        )

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str = "You are an expert software engineer.",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Convenience method: system prompt + user prompt → response."""
        messages: list[BaseMessage] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]
        return await self.chat(
            messages, temperature=temperature, max_tokens=max_tokens
        )
