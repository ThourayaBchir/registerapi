from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row

from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Data access for user records."""

    async def create_user(self, email: str, password_hash: str) -> int:
        query = (
            "INSERT INTO users (email, password_hash) "
            "VALUES (%(email)s, %(password_hash)s) RETURNING id"
        )
        async with self.connection.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, {"email": email, "password_hash": password_hash})
            record = await cur.fetchone()
        await self.connection.commit()
        return int(record["id"])  # type: ignore[index]

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        query = "SELECT id, email, password_hash, is_active, created_at, updated_at FROM users WHERE email = %(email)s"
        async with self.connection.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, {"email": email})
            record = await cur.fetchone()
        return record  # type: ignore[return-value]

    async def activate_user(self, email: str) -> None:
        query = "UPDATE users SET is_active = TRUE WHERE email = %(email)s"
        async with self.connection.cursor() as cur:
            await cur.execute(query, {"email": email})
        await self.connection.commit()
