from abc import ABC, abstractmethod

from app.tasks.email import send_activation_email


class EmailService(ABC):
    @abstractmethod
    async def send_activation(self, email: str, code: str) -> None:
        raise NotImplementedError


class CeleryEmailService(EmailService):
    """Email service backed by Celery tasks."""

    async def send_activation(self, email: str, code: str) -> None:
        send_activation_email.delay(email, code)
