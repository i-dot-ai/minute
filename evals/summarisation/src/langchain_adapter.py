from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ConfigDict

from common.llm.adapters.base import ModelAdapter


class LangChainModelAdapter(BaseChatModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    adapter: Any
    model_name: str

    def __init__(self, adapter: ModelAdapter, model_name: str, **kwargs: Any) -> None:
        super().__init__(adapter=adapter, model_name=model_name, **kwargs)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        message_dicts = [{"role": "user" if i == 0 else "assistant", "content": str(m.content)} for i, m in enumerate(messages)]

        response = loop.run_until_complete(self.adapter.chat(message_dicts))

        message = AIMessage(content=response)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        return "langchain_model_adapter"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model_name": self.model_name}
