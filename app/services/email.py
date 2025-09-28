from __future__ import annotations

from app.tasks.email import send_activation_email


class EmailService:
    async def send_activation(self, email: str, code: str, ttl_seconds: int) -> None:
        raise NotImplementedError


class CeleryEmailService(EmailService):
    """Email service backed by Celery tasks."""

    def __init__(self, queue: str | None = None) -> None:
        self._queue = queue

    async def send_activation(self, email: str, code: str, ttl_seconds: int) -> None:
        send_activation_email.delay(email, code, ttl_seconds)
