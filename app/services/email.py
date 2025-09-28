from abc import ABC, abstractmethod


class EmailService(ABC):
    @abstractmethod
    async def send_activation(self, email: str, code: str) -> None:
        raise NotImplementedError
