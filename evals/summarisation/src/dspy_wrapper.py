from __future__ import annotations

import asyncio
import logging
from typing import Any

import dspy

from common.llm.adapters.base import ModelAdapter

logger = logging.getLogger(__name__)


class DSPyModelAdapterWrapper(dspy.LM):
    def __init__(self, adapter: ModelAdapter, model_name: str, **kwargs: Any) -> None:
        super().__init__(model=model_name, **kwargs)
        self.adapter = adapter
        self.history: list[dict[str, Any]] = []

    def __call__(
        self,
        prompt: str | None = None,
        messages: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> list[str]:
        if messages is None and prompt is None:
            msg = "Either prompt or messages must be provided"
            raise ValueError(msg)

        if messages is None:
            messages = [{"role": "user", "content": prompt}]

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        response = loop.run_until_complete(self.adapter.chat(messages))

        self.history.append(
            {
                "messages": messages,
                "response": response,
                "kwargs": kwargs,
            }
        )

        return [response]

    def inspect_history(self, n: int = 1) -> list[dict[str, Any]]:
        return self.history[-n:] if self.history else []
