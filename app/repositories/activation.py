from __future__ import annotations

from datetime import datetime, timedelta, timezone

from psycopg.rows import dict_row

from app.repositories.base import BaseRepository


class ActivationRepository(BaseRepository):
    """Data access for activation codes."""

    async def create_code(self, email: str, code: str, ttl_seconds: int = 60) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        query = (
            "INSERT INTO activation_codes (email, code, expires_at) "
            "VALUES (%(email)s, %(code)s, %(expires_at)s)"
        )
        async with self.connection.cursor() as cur:
            await cur.execute(
                query,
                {
                    "email": email,
                    "code": code,
                    "expires_at": expires_at,
                },
            )
        await self.connection.commit()

    async def validate_code(self, email: str, code: str) -> bool:
        query = (
            "UPDATE activation_codes "
            "SET used_at = NOW() "
            "WHERE email = %(email)s AND code = %(code)s "
            "  AND used_at IS NULL AND expires_at > NOW() "
            "RETURNING id"
        )
        async with self.connection.cursor() as cur:
            await cur.execute(query, {"email": email, "code": code})
            record = await cur.fetchone()
        await self.connection.commit()
        return record is not None

    async def latest_code(self, email: str) -> dict | None:
        query = (
            "SELECT id, email, code, expires_at, used_at, created_at "
            "FROM activation_codes WHERE email = %(email)s "
            "ORDER BY created_at DESC LIMIT 1"
        )
        async with self.connection.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, {"email": email})
            record = await cur.fetchone()
        return record  # type: ignore[return-value]

    async def purge_expired(self) -> int:
        query = (
            "DELETE FROM activation_codes WHERE expires_at <= NOW() AND used_at IS NULL"
        )
        async with self.connection.cursor() as cur:
            await cur.execute(query)
            rowcount = cur.rowcount
        await self.connection.commit()
        return rowcount
