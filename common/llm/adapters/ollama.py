import json
import logging
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionDeveloperMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from pydantic import BaseModel

from common.settings import get_settings

from .base import ModelAdapter

settings = get_settings()
logger = logging.getLogger(__name__)


class OllamaModelAdapter(ModelAdapter):
    def __init__(
        self,
        model: str,
        base_url: str,
        **kwargs: Any,
    ) -> None:
        self._model = model
        self.async_client = AsyncOpenAI(
            base_url=base_url,
            api_key="ollama",
        )
        self._kwargs = kwargs

    @staticmethod
    def _convert_to_openai_message(msg: dict[str, str]) -> ChatCompletionMessageParam:
        role = msg["role"]
        content = msg["content"]

        if role == "system":
            return ChatCompletionSystemMessageParam(role="system", content=content)
        elif role == "user":
            return ChatCompletionUserMessageParam(role="user", content=content)
        elif role == "assistant":
            return ChatCompletionAssistantMessageParam(role="assistant", content=content)
        elif role == "developer":
            return ChatCompletionDeveloperMessageParam(role="developer", content=content)
        else:
            error_msg = f"Invalid role: {role}"
            raise ValueError(error_msg)

    async def structured_chat[T: BaseModel](self, messages: list[dict[str, str]], response_format: type[T]) -> T:
        schema = response_format.model_json_schema()
        json_instruction = f"\n\nRespond with valid JSON matching this schema:\n{schema}"

        modified_messages = messages.copy()
        if modified_messages:
            last_msg = modified_messages[-1].copy()
            last_msg["content"] = last_msg["content"] + json_instruction
            modified_messages[-1] = last_msg

        openai_messages = [self._convert_to_openai_message(msg) for msg in modified_messages]

        response = await self.async_client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            response_format={"type": "json_object"},
            temperature=self._kwargs.get("temperature", 0.0),
        )

        content = response.choices[0].message.content
        if content is None:
            msg = "Received empty response from Ollama"
            raise ValueError(msg)
        try:
            json_data = json.loads(content)
            return response_format.model_validate(json_data)
        except Exception as e:
            logger.error("Ollama JSON parsing/validation failed: %s: %s", type(e).__name__, str(e))
            raise

    async def chat(self, messages: list[dict[str, str]]) -> str:
        try:
            openai_messages = [self._convert_to_openai_message(msg) for msg in messages]

            response = await self.async_client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=0.0,
            )

            content = response.choices[0].message.content
            if content is None:
                msg = "Received empty response from Ollama"
                raise ValueError(msg)
            return content
        except Exception as e:
            logger.error("Ollama chat failed: %s: %s", type(e).__name__, str(e))
            raise
