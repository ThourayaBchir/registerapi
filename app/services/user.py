from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.core.security import hash_password
from app.repositories.activation import ActivationRepository
from app.repositories.user import UserRepository
from app.services.email import EmailService
from app.utils.code_generator import generate_code


class UserAlreadyActiveError(Exception):
    """Raised when the user is already activated."""


class UserPendingActivationError(Exception):
    """Raised when a registration attempt is made for a pending user."""


class UserNotFoundError(Exception):
    """Raised when attempting to request a code for a non-existent user."""


@dataclass
class ActivationResult:
    email: str
    code: str


class UserService:
    def __init__(
        self,
        users: UserRepository,
        activation_codes: ActivationRepository,
        email_service: EmailService,
        settings: Settings,
    ) -> None:
        self._users = users
        self._activation_codes = activation_codes
        self._email_service = email_service
        self._settings = settings

    async def register(self, email: str, password: str) -> ActivationResult:
        password_hash = hash_password(password)
        existing_user = await self._users.get_user_by_email(email)
        if existing_user:
            if existing_user.get("is_active"):
                raise UserAlreadyActiveError(f"User {email} is already active")
            raise UserPendingActivationError(
                f"User {email} already registered and pending activation"
            )

        await self._users.create_user(email, password_hash)
        return await self._issue_activation_code(email)

    async def request_activation_code(self, email: str) -> ActivationResult:
        user = await self._users.get_user_by_email(email)
        if user is None:
            raise UserNotFoundError(f"User {email} not found")
        if user.get("is_active"):
            raise UserAlreadyActiveError(f"User {email} is already active")

        return await self._issue_activation_code(email)

    async def activate(self, email: str, code: str) -> bool:
        is_valid = await self._activation_codes.validate_code(email, code)
        if not is_valid:
            return False

        await self._users.activate_user(email)
        return True

    async def _issue_activation_code(self, email: str) -> ActivationResult:
        code = generate_code()
        await self._activation_codes.create_code(
            email=email,
            code=code,
            ttl_seconds=self._settings.activation_code_ttl_seconds,
        )
        await self._email_service.send_activation(email, code)
        return ActivationResult(email=email, code=code)
