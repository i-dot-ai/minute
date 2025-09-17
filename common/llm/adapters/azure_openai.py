import logging
from typing import TypeVar

from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice

from common.settings import get_settings

from .base import ModelAdapter

settings = get_settings()
T = TypeVar("T")
logger = logging.getLogger(__name__)


class OpenAIModelAdapter(ModelAdapter):
    def __init__(
        self,
        model: str,
        api_key: str,
        azure_endpoint: str,
        azure_deployment: str,
        api_version: str = "2024-08-01-preview",
        **kwargs,
    ) -> None:
        self._model = model
        self.async_azure_client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
            azure_deployment=azure_deployment,
        )
        self._kwargs = kwargs

        self._messages = []

    @property
    def messages(self) -> list[dict[str, str]]:
        return self._messages

    @messages.setter
    def messages(self, messages: list[dict[str, str]]) -> None:
        self._messages = messages

    async def structured_chat(self, messages: list[dict[str, str]], response_format: type[T]) -> T:
        self._messages.extend(messages)
        response = await self.async_azure_client.beta.chat.completions.parse(
            model=self._model, messages=messages, response_format=response_format, **self._kwargs
        )
        choice = self.handle_response(response)

        return choice.message.parsed

    async def chat(self, messages: list[dict[str, str]]) -> str:
        self._messages.extend(messages)
        response = await self.async_azure_client.chat.completions.create(
            model=self._model,
            messages=self._messages,
            temperature=0.0,
            max_tokens=16384,
        )
        choice = self.handle_response(response)
        return choice.message.content

    def handle_response(self, response: ChatCompletion) -> Choice:
        choice: Choice = response.choices[0]

        self._messages.append({"role": "assistant", "content": choice.message.content})
        # Note, currently we don't handle incomplete responses - we only call this to log the warning
        self.choice_incomplete(choice, response)
        return choice

    @staticmethod
    def choice_incomplete(choice: Choice, response: ChatCompletion) -> bool:
        if choice.finish_reason == "length":
            logger.warning(
                "max output tokens reached: ID: %s prompt_tokens: %s completion_tokens %s",
                response.id,
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
            return True
        return False
