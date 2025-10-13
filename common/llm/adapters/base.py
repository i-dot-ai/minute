from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from common.settings import get_settings

settings = get_settings()
T = TypeVar("T", bound=BaseModel)


class ModelAdapter(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> Any: ...
    async def structured_chat(self, messages: list[dict[str, str]], response_format: type[T]) -> T: ...
