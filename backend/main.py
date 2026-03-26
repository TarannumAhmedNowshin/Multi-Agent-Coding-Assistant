"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.dependencies import _cache_service
from backend.api.middleware import register_middleware
from backend.api.routes import health, index, search, tasks, ws
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

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Middleware (request ID, error handling) ──
register_middleware(app)

# ── Routes ──
app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(index.router)
app.include_router(search.router)
app.include_router(ws.router)
