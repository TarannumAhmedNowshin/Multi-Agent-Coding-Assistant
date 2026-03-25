"""FastAPI dependency injection providers."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.engine import async_session_factory
from backend.services.cache_service import CacheService

# Singleton cache service instance
_cache_service = CacheService()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_cache() -> CacheService:
    """Provide the cache service singleton."""
    return _cache_service
