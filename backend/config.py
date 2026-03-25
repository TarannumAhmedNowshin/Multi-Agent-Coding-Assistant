"""Centralized application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──
    app_env: str = "development"
    log_level: str = "INFO"

    # ── Azure OpenAI (Chat) ──
    azure_openai_api_key: str
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_endpoint: str
    azure_openai_model: str = "gpt-4o"

    # ── Azure OpenAI (Embeddings) ──
    embed_api_key: str
    embed_api_version: str = "2023-05-15"
    embed_deployment: str = "text-embedding-3-small"
    embed_endpoint: str
    embed_model: str = "text-embedding-3-small"
    embed_dimensions: int = 972

    # ── PostgreSQL ──
    database_url: str

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── LangSmith ──
    langsmith_api_key: str = ""
    langsmith_project: str = "agentic-developer"
    langsmith_tracing: str = "true"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
