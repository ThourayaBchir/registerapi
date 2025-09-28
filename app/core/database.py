"""Database connection management using psycopg connection pools."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings

_POOL: AsyncConnectionPool | None = None


def get_pool() -> AsyncConnectionPool:
    """Return a singleton async connection pool."""
    global _POOL
    if _POOL is None:
        settings = get_settings()
        _POOL = AsyncConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=10,
            timeout=30,
            open=False,
        )
    return _POOL


async def init_pool() -> AsyncConnectionPool:
    pool = get_pool()
    await pool.open()
    return pool


async def close_pool() -> None:
    global _POOL
    if _POOL is not None:
        await _POOL.close()
        _POOL = None


@asynccontextmanager
async def get_db_conn() -> AsyncIterator[AsyncConnection]:
    pool = get_pool()
    async with pool.connection() as conn:
        yield conn
