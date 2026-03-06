from __future__ import annotations

import logging
from typing import Any, cast

from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.chat.chat_completion import Choice

from common.settings import get_settings

from .base import ModelAdapter
from .llm_constants import MAX_TOKENS, TEMPERATURE

settings = get_settings()
logger = logging.getLogger(__name__)


class OpenAIModelAdapter(ModelAdapter):
    def __init__(
        self,
        model: str,
        api_key: str,
        azure_endpoint: str,
        azure_deployment: str,
        api_version: str = "2024-08-01-preview",
        **kwargs: Any,
    ) -> None:
        self._model = model
        self.async_azure_client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
            azure_deployment=azure_deployment,
        )
        self._kwargs = kwargs

    async def structured_chat[T](self, messages: list[dict[str, str]], response_format: type[T]) -> T:
        response = await self.async_azure_client.beta.chat.completions.parse(
            model=self._model,
            messages=cast(list[ChatCompletionMessageParam], messages),
            response_format=response_format,
            **self._kwargs,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            msg = "OpenAI response.parsed is None"
            raise ValueError(msg)
        return cast(T, parsed)

    async def chat(self, messages: list[dict[str, str]]) -> str:
        response = await self.async_azure_client.chat.completions.create(
            model=self._model,
            messages=cast(list[ChatCompletionMessageParam], messages),
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        choice = response.choices[0]
        self.choice_incomplete(choice, response)
        message_content = choice.message.content
        if message_content is None:
            msg = "OpenAI response.content is None"
            raise ValueError(msg)
        return message_content

    @staticmethod
    def choice_incomplete(choice: Choice, response: ChatCompletion) -> bool:
        if choice.finish_reason == "length":
            logger.warning(
                "max output tokens reached: ID: %s prompt_tokens: %s completion_tokens %s",
                response.id,
                response.usage.prompt_tokens if response.usage else None,
                response.usage.completion_tokens if response.usage else None,
            )
            return True
        return False
