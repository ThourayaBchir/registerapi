from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Data access for user records."""

    async def create_user(self, email: str, password_hash: str) -> int:
        raise NotImplementedError

    async def get_user_by_email(self, email: str):
        raise NotImplementedError
