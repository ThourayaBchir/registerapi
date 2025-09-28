"""Base repository with shared helpers for executing SQL statements."""

from __future__ import annotations

from typing import Any, Mapping

from psycopg import AsyncConnection


class BaseRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    @property
    def connection(self) -> AsyncConnection:
        return self._connection

    async def _execute(
        self,
        query: str,
        params: Mapping[str, Any] | None = None,
    ) -> int:
        async with self.connection.cursor() as cur:
            await cur.execute(query, params)
            affected = cur.rowcount
        await self.connection.commit()
        return affected

    async def _fetch_one(
        self,
        query: str,
        params: Mapping[str, Any] | None = None,
        *,
        row_factory: Any | None = None,
        commit: bool = False,
    ) -> Any:
        async with self.connection.cursor(row_factory=row_factory) as cur:
            await cur.execute(query, params)
            record = await cur.fetchone()
        if commit:
            await self.connection.commit()
        return record
