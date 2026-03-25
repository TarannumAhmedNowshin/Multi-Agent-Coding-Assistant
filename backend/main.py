"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from backend.api.dependencies import _cache_service
from backend.api.routes import health
from backend.utils.logger import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle hooks."""
    setup_logging()
    logger.info("Starting Agentic Developer API")

    # Connect Redis
    try:
        await _cache_service.connect()
    except Exception:
        logger.warning("Redis unavailable — caching disabled")

    yield

    # Shutdown
    await _cache_service.disconnect()
    logger.info("Agentic Developer API stopped")


app = FastAPI(
    title="Agentic Developer API",
    description="AI-powered multi-agent coding assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Routes ──
app.include_router(health.router)
