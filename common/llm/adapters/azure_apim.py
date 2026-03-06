from __future__ import annotations

import logging
from typing import cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.chat.chat_completion import Choice

from .base import ModelAdapter
from .llm_constants import MAX_TOKENS, TEMPERATURE

logger = logging.getLogger(__name__)


class AzureAPIMModelAdapter(ModelAdapter):
    def __init__(
        self,
        url: str,
        model: str,
        api_version: str,
        access_token: str,
        subscription_key: str,
    ) -> None:
        self._model = model
        self._api_version = api_version
        self.async_apim_client = AsyncOpenAI(
            base_url=url + self._model,  # APIM URL expects model here
            api_key=access_token,
            default_headers={
                "Ocp-Apim-Subscription-Key": subscription_key,
            },
        )

    async def structured_chat[T](self, messages: list[dict[str, str]], response_format: type[T]) -> T:
        response = await self.async_apim_client.beta.chat.completions.parse(
            model=self._model,
            messages=cast(list[ChatCompletionMessageParam], messages),
            response_format=response_format,
            extra_query={"api-version": self._api_version},
        )

        parsed = response.choices[0].message.parsed
        if parsed is None:
            msg = "Azure APIM response.parsed is None"
            raise ValueError(msg)
        return cast(T, parsed)

    async def chat(self, messages: list[dict[str, str]]) -> str:
        response = await self.async_apim_client.chat.completions.create(
            model=self._model,
            messages=cast(list[ChatCompletionMessageParam], messages),
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            extra_query={"api-version": self._api_version},
        )

        choice = response.choices[0]
        self.choice_incomplete(choice, response)
        message_content = choice.message.content
        if message_content is None:
            msg = "Azure APIM message.content is None"
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
