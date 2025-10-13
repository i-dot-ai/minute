import logging
from typing import TypeVar

from google import genai
from google.genai import types
from google.genai.types import (
    Content,
    GenerateContentConfig,
    HttpOptions,
    ModelContent,
    Part,
    UserContent,
)

from common.settings import get_settings

from .base import ModelAdapter

settings = get_settings()
T = TypeVar("T")
logger = logging.getLogger(__name__)


class GeminiModelAdapter(ModelAdapter):
    def __init__(
        self,
        model: str,
        generate_content_config: GenerateContentConfig,
        http_options: HttpOptions | None = None,
        **kwargs,
    ) -> None:
        self.generate_content_config = generate_content_config
        self._model = model
        # Note, env vars GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS are automatically used by the client
        # GOOGLE_CLOUD_LOCATION 'should' also be according to docs, but this doesn't appear to be true...
        self.client = genai.Client(http_options=http_options, vertexai=True, location=settings.GOOGLE_CLOUD_LOCATION)
        self._kwargs = kwargs

    @staticmethod
    def no_safety_settings() -> list[types.SafetySetting]:
        return [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
        ]

    def _convert_openai_messages_to_gemini(self, messages: list[dict[str, str]]) -> tuple[list[Content], Content]:
        gemini_messages = []
        system_instructions = []
        for message in messages:
            if message["role"] == "user":
                gemini_messages.append(UserContent(parts=[Part.from_text(text=message["content"])]))
            elif message["role"] == "assistant":
                gemini_messages.append(ModelContent(parts=[Part.from_text(text=message["content"])]))
            elif message["role"] == "system":
                system_instructions.append(message["content"])
            else:
                msg = f"Invalid role: {message['role']}"
                logger.warning(msg)
        return gemini_messages, Content(parts=[Part.from_text(text=instruction) for instruction in system_instructions])

    async def structured_chat(self, messages: list[dict[str, str]], response_format: type[T]) -> T:
        contents, system_instruction = self._convert_openai_messages_to_gemini(messages)
        response = await self.client.aio.models.generate_content(
            contents=contents,
            model=self._model,
            config=self.generate_content_config.model_copy(
                update={
                    "response_mime_type": "application/json",
                    "response_schema": response_format,
                    "system_instruction": system_instruction,
                }
            ),
        )
        return response.parsed

    async def chat(self, messages: list[dict[str, str]]) -> str:
        contents, system_instruction = self._convert_openai_messages_to_gemini(messages)
        response = await self.client.aio.models.generate_content(
            contents=contents,
            model=self._model,
            config=self.generate_content_config.model_copy(update={"system_instruction": system_instruction}),
        )
        return response.text
