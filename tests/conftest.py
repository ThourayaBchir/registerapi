"""Shared pytest fixtures for database-backed tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import pytest_asyncio
import psycopg
from psycopg import AsyncConnection
from psycopg.rows import dict_row

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "db" / "migrations"


async def _apply_migrations(connection: AsyncConnection) -> None:
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        sql = migration.read_text(encoding="utf-8")
        if sql.strip():
            await connection.execute(sql)
    await connection.commit()


@pytest_asyncio.fixture
async def db_conn() -> AsyncConnection:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL environment variable is not set")

    connection = await psycopg.AsyncConnection.connect(database_url)
    connection.row_factory = dict_row

    await _apply_migrations(connection)

    yield connection

    try:
        await connection.execute("TRUNCATE TABLE activation_codes RESTART IDENTITY CASCADE")
        await connection.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE")
        await connection.commit()
    finally:
        await connection.close()
