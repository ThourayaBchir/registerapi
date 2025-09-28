"""Redis-backed rate limiter used by auth flows."""

from __future__ import annotations

from redis.asyncio import Redis

from app.core import constants


class RateLimitExceeded(Exception):
    def __init__(self, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class RateLimiter:
    """Minimal Redis-backed limiter for activation attempts and resends."""
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    # Activation ---------------------------------------------------------

    async def ensure_activation_allowed(self, email: str) -> None:
        ttl = await self._redis.ttl(self._activation_lock_key(email))
        if ttl and ttl > 0:
            raise RateLimitExceeded(
                "Too many activation attempts. Please try again later.",
                retry_after=ttl,
            )

    async def record_activation_failure(self, email: str) -> None:
        attempts_key = self._activation_attempts_key(email)
        attempts = await self._redis.incr(attempts_key)
        if attempts == 1:
            await self._redis.expire(attempts_key, constants.ACTIVATION_ATTEMPT_WINDOW_SECONDS)

        if attempts >= constants.ACTIVATION_ATTEMPT_LIMIT:
            await self._redis.set(
                self._activation_lock_key(email),
                "1",
                ex=constants.ACTIVATION_LOCK_SECONDS,
            )
            await self._redis.delete(attempts_key)

    async def reset_activation(self, email: str) -> None:
        await self._redis.delete(self._activation_attempts_key(email))
        await self._redis.delete(self._activation_lock_key(email))

    # Resend -------------------------------------------------------------

    async def ensure_resend_allowed(self, email: str) -> None:
        minute_ttl = await self._redis.ttl(self._resend_minute_key(email))
        if (
            constants.RESEND_PER_MINUTE_LIMIT > 0
            and minute_ttl
            and minute_ttl > 0
        ):
            raise RateLimitExceeded(
                "Too many resend requests. Please wait before trying again.",
                retry_after=minute_ttl,
            )

        daily_count = await self._redis.get(self._resend_daily_key(email))
        if daily_count is None:
            return

        if int(daily_count) >= constants.RESEND_DAILY_LIMIT:
            ttl = await self._redis.ttl(self._resend_daily_key(email))
            raise RateLimitExceeded(
                "Daily resend limit reached. Please try again later.",
                retry_after=ttl if ttl and ttl > 0 else None,
            )

    async def record_resend(self, email: str) -> None:
        minute_key = self._resend_minute_key(email)
        if constants.RESEND_PER_MINUTE_LIMIT > 0:
            await self._redis.set(minute_key, "1", ex=constants.RESEND_MINUTE_WINDOW_SECONDS)

        daily_key = self._resend_daily_key(email)
        total = await self._redis.incr(daily_key)
        if total == 1:
            await self._redis.expire(daily_key, constants.RESEND_DAILY_WINDOW_SECONDS)

    # Key helpers --------------------------------------------------------

    def _activation_attempts_key(self, email: str) -> str:
        return f"activation:attempts:{email.lower()}"

    def _activation_lock_key(self, email: str) -> str:
        return f"activation:lock:{email.lower()}"

    def _resend_minute_key(self, email: str) -> str:
        return f"resend:minute:{email.lower()}"

    def _resend_daily_key(self, email: str) -> str:
        return f"resend:daily:{email.lower()}"


__all__ = ["RateLimiter", "RateLimitExceeded"]
