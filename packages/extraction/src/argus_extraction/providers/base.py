from abc import ABC, abstractmethod

from pydantic import BaseModel


class Provider(ABC):
    name: str

    @abstractmethod
    async def structured_extract(
        self,
        prompt: str,
        schema: type[BaseModel],
        model: str,
    ) -> BaseModel: ...

    @abstractmethod
    async def text_complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 512,
    ) -> str: ...
