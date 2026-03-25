"""Redis caching service for LLM responses and intermediate results."""

import hashlib
import json
import logging

import redis.asyncio as redis

from backend.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Async Redis cache with JSON serialization."""

    def __init__(self) -> None:
        self._pool: redis.Redis | None = None

    async def connect(self) -> None:
        """Initialize the Redis connection pool."""
        self._pool = redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        await self._pool.ping()
        logger.info("Connected to Redis at %s", settings.redis_url)

    async def disconnect(self) -> None:
        """Close the Redis connection pool."""
        if self._pool:
            await self._pool.aclose()
            logger.info("Disconnected from Redis")

    @property
    def pool(self) -> redis.Redis:
        if self._pool is None:
            raise RuntimeError("CacheService not connected. Call connect() first.")
        return self._pool

    @staticmethod
    def _make_key(namespace: str, identifier: str) -> str:
        """Build a cache key: namespace:sha256(identifier)."""
        digest = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"agentic:{namespace}:{digest}"

    async def get(self, namespace: str, identifier: str) -> dict | None:
        """Retrieve a cached value, or None if missing/expired."""
        key = self._make_key(namespace, identifier)
        raw = await self.pool.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(
        self,
        namespace: str,
        identifier: str,
        value: dict,
        ttl_seconds: int = 3600,
    ) -> None:
        """Store a value in cache with a TTL (default 1 hour)."""
        key = self._make_key(namespace, identifier)
        await self.pool.set(key, json.dumps(value), ex=ttl_seconds)

    async def delete(self, namespace: str, identifier: str) -> None:
        """Remove a cached entry."""
        key = self._make_key(namespace, identifier)
        await self.pool.delete(key)

    async def flush_namespace(self, namespace: str) -> int:
        """Delete all keys in a namespace. Returns count deleted."""
        pattern = f"agentic:{namespace}:*"
        count = 0
        async for key in self.pool.scan_iter(match=pattern, count=100):
            await self.pool.delete(key)
            count += 1
        return count
