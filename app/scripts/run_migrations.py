"""Apply SQL migrations in app/db/migrations against the configured database."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Iterable

from psycopg import AsyncConnection

from app.core.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"


def _load_migrations() -> Iterable[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


async def _apply_migration(connection: AsyncConnection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8").strip()
    if not sql:
        return
    print(f"Applying {path.name}...")
    await connection.execute(sql)


async def _run() -> None:
    settings = get_settings()
    migrations = list(_load_migrations())
    if not migrations:
        print("No migrations found.")
        return

    async with await AsyncConnection.connect(settings.database_url) as connection:
        for migration in migrations:
            await _apply_migration(connection, migration)
        await connection.commit()

    print("Migrations applied successfully.")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
