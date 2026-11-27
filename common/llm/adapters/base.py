from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ModelAdapter(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> str: ...
    async def structured_chat(self, messages: list[dict[str, str]], response_format: type[T]) -> T: ...


class StructuredOutputError(RuntimeError):
    """The model did not return the structured response it was asked for."""
