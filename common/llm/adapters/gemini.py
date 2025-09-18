import logging
from typing import TypeVar

from google import genai
from google.genai import types
from google.genai.types import (
    Content,
    GenerateContentConfig,
    GenerateContentResponse,
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
        self._system_instruction: Content | None = None
        self.generate_content_config = generate_content_config
        self._model = model
        # Note, env vars GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS are automatically used by the client
        # GOOGLE_CLOUD_LOCATION 'should' also be according to docs, but this doesn't appear to be true...
        self.client = genai.Client(http_options=http_options, vertexai=True, location=settings.GOOGLE_CLOUD_LOCATION)
        self._kwargs = kwargs
        self._messages = []

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

    def _convert_openai_messages_to_gemini(self) -> list[Content]:
        gemini_messages = []
        for message in self._messages:
            if message["role"] == "user":
                gemini_messages.append(UserContent(parts=[Part.from_text(text=message["content"])]))
            elif message["role"] == "assistant":
                gemini_messages.append(ModelContent(parts=[Part.from_text(text=message["content"])]))
            elif message["role"] == "system":
                if self._system_instruction and self._system_instruction.parts[0].text != message["content"]:
                    logger.warning("system instruction already set - ignoring new system instruction")
                else:
                    self._system_instruction = Content(parts=[Part.from_text(text=message["content"])])
            else:
                msg = f"Invalid role: {message['role']}"
                raise ValueError(msg)
        return gemini_messages

    def handle_response(self, response: GenerateContentResponse) -> None:
        self._messages.append({"role": "assistant", "content": response.text})

    async def structured_chat(self, messages: list[dict[str, str]], response_format: type[T]) -> T:
        self._messages.extend(messages)
        response = await self.client.aio.models.generate_content(
            contents=self._convert_openai_messages_to_gemini(),
            model=self._model,
            config=self.generate_content_config.model_copy(
                update={
                    "response_mime_type": "application/json",
                    "response_schema": response_format,
                    "system_instruction": self._system_instruction,
                }
            ),
        )
        self.handle_response(response)
        return response.parsed

    async def chat(self, messages: list[dict[str, str]]) -> str:
        self._messages.extend(messages)
        response = await self.client.aio.models.generate_content(
            contents=self._convert_openai_messages_to_gemini(),
            model=self._model,
            config=self.generate_content_config.model_copy(update={"system_instruction": self._system_instruction}),
        )
        self.handle_response(response)
        return response.text

    @property
    def messages(self) -> list[dict[str, str]]:
        return self._messages

    @messages.setter
    def messages(self, messages: list[dict[str, str]]) -> None:
        self._messages = messages
