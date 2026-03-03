from typing import Protocol

from pydantic import BaseModel

from common.settings import get_settings

settings = get_settings()


class ModelAdapter(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> str: ...
    async def structured_chat[T: BaseModel](self, messages: list[dict[str, str]], response_format: type[T]) -> T: ...
