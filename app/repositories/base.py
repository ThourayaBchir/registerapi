"""Base repository with shared helpers for executing SQL statements."""

from __future__ import annotations

from abc import ABC

from psycopg import AsyncConnection


class BaseRepository(ABC):
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    @property
    def connection(self) -> AsyncConnection:
        return self._connection
