from typing import Any, Protocol, TypeVar

from common.settings import get_settings

settings = get_settings()
T = TypeVar("T")


class ModelAdapter(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> Any: ...
    async def structured_chat(self, messages: list[dict[str, str]], response_format: type[T]) -> T: ...
    @property
    def messages(self) -> list[dict[str, str]]: ...
    @messages.setter
    def messages(self, messages: list[dict[str, str]]) -> None: ...
