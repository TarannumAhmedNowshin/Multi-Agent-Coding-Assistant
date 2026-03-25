"""Structured logging setup with optional LangSmith integration."""

import logging
import os
import sys

from backend.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if not settings.is_production else logging.WARNING
    )

    # ── LangSmith environment variables ──
    if settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = settings.langsmith_tracing
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        logging.getLogger(__name__).info(
            "LangSmith tracing enabled for project: %s",
            settings.langsmith_project,
        )
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logging.getLogger(__name__).info(
            "LangSmith tracing disabled (no API key configured)"
        )
