from __future__ import annotations

from app.repositories.activation import ActivationRepository
from app.repositories.user import UserRepository


class ActivationService:
    def __init__(self, codes: ActivationRepository, users: UserRepository) -> None:
        self._codes = codes
        self._users = users

    async def verify(self, email: str, code: str) -> bool:
        is_valid = await self._codes.validate_code(email, code)
        if not is_valid:
            return False

        await self._users.activate_user(email)
        return True

    async def resend_code(self, email: str, code: str, ttl_seconds: int) -> None:
        await self._codes.create_code(email, code, ttl_seconds)
