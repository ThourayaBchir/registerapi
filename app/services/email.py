from abc import ABC, abstractmethod

from app.tasks.email import send_activation_email


class EmailService(ABC):
    @abstractmethod
    async def send_activation(self, email: str, code: str, ttl_seconds: int) -> None:
        raise NotImplementedError


class CeleryEmailService(EmailService):
    """Email service backed by Celery tasks."""

    def __init__(self, queue: str | None = None) -> None:
        self._queue = queue

    async def send_activation(self, email: str, code: str, ttl_seconds: int) -> None:
        send_activation_email.apply_async(args=(email, code, ttl_seconds), queue=self._queue)
