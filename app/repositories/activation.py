from app.repositories.base import BaseRepository


class ActivationRepository(BaseRepository):
    """Data access for activation codes."""

    async def create_code(self, email: str, code: str) -> None:
        raise NotImplementedError

    async def validate_code(self, email: str, code: str) -> bool:
        raise NotImplementedError
