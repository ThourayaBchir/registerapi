"""Redis client management limited to Celery broker usage."""

from __future__ import annotations

import redis.asyncio as redis

from app.core.config import get_settings

_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Return a singleton Redis client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def init_redis() -> redis.Redis:
    client = get_redis_client()
    await client.ping()
    return client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
