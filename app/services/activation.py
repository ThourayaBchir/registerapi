from app.repositories.activation import ActivationRepository


class ActivationService:
    def __init__(self, codes: ActivationRepository) -> None:
        self._codes = codes

    async def verify(self, email: str, code: str) -> bool:
        return await self._codes.validate_code(email, code)
