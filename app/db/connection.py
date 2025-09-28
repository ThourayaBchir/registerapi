"""Expose higher level database helpers built on top of the core pool."""

from contextlib import asynccontextmanager

from psycopg import AsyncCursor

from app.core.database import get_db_conn


@asynccontextmanager
async def get_cursor() -> AsyncCursor:
    async for conn in get_db_conn():
        async with conn.cursor() as cur:
            yield cur
