from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ConfigDict, Field

from common.llm.adapters.base import ModelAdapter


def _convert_message_to_dict(message: BaseMessage) -> dict[str, str]:
    role = "user" if message.type == "human" else message.type
    return {"role": role, "content": str(message.content)}


class LangChainModelAdapter(BaseChatModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    adapter: Any = Field(default=None)
    model_name: str = Field(default="")

    def __init__(self, adapter: ModelAdapter, model_name: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.adapter = adapter
        self.model_name = model_name

    def _generate(  # type: ignore[override]
        self,
        messages: list[BaseMessage],
        _stop: list[str] | None = None,
        _run_manager: CallbackManagerForLLMRun | None = None,
        **_kwargs: Any,
    ) -> ChatResult:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        message_dicts = [_convert_message_to_dict(m) for m in messages]

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
