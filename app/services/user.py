from app.repositories.user import UserRepository
from app.services.email import EmailService
from app.utils.code_generator import generate_code


class UserService:
    def __init__(self, users: UserRepository, email_service: EmailService) -> None:
        self._users = users
        self._email_service = email_service

    async def register(self, email: str, password: str) -> None:
        code = generate_code()
        await self._email_service.send_activation(email, code)
