"""Gemini chat client for every worker LLM call.

`ChatBot` is the Protocol every caller depends on; `GeminiChatBot` is the only
implementation today. Keeping the interface named (rather than exposing the Gemini
class directly) is the seam to add a second provider behind, without callers changing.
"""

from enum import Enum, auto
from typing import Protocol, TypeVar, cast

from google import genai
from google.genai import types
from google.genai.types import Content, GenerateContentConfig, ModelContent, Part, UserContent
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_random_exponential

from common.settings import get_settings, get_structured_logger

settings = get_settings()
slogger = get_structured_logger()
T = TypeVar("T", bound=BaseModel)

# Gemini 3 models are tuned to run at their default temperature of 1.0. Google warns that
# lowering it can cause looping and degraded reasoning, particularly on the long transcripts
# we send for minute generation. Callers that genuinely need determinism can still pass an
# explicit temperature to create_chatbot.
DEFAULT_TEMPERATURE = 1.0


def _no_safety_settings() -> list[types.SafetySetting]:
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


def _to_gemini_contents(messages: list[dict[str, str]]) -> tuple[list[Content], Content]:
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
            slogger.warning(msg)
    return gemini_messages, Content(parts=[Part.from_text(text=instruction) for instruction in system_instructions])


class ChatBot(Protocol):
    """Contract for a chat model.

    Structural: test doubles and any future provider conform without inheriting.
    """

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Return a free-text reply.

        :param messages: Chat messages (``role``/``content``) to send.
        :returns: The model's text response.
        """
        ...

    async def structured_chat(self, messages: list[dict[str, str]], response_format: type[T]) -> T:
        """Return a reply parsed into ``response_format``.

        :param messages: Chat messages (``role``/``content``) to send.
        :param response_format: Pydantic model the response is parsed into.
        :returns: The parsed model instance.
        """
        ...


class GeminiChatBot(ChatBot):
    """Gemini conversation implementation with retry and conversation-history tracking.

    Callers get two entry points: `chat` for free-text responses and `structured_chat`
    for responses parsed into a pydantic model. Both retry transient failures with
    jittered backoff and accumulate the conversation in `self.messages`, so follow-up
    calls see previous turns."""

    def __init__(self, model_name: str, temperature: float = DEFAULT_TEMPERATURE) -> None:
        self._model = model_name
        self._base_config = GenerateContentConfig(safety_settings=_no_safety_settings(), temperature=temperature)
        # Note, env vars GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS are automatically used by the client
        # GOOGLE_CLOUD_LOCATION 'should' also be according to docs, but this doesn't appear to be true...
        self._client = genai.Client(vertexai=True, location=settings.GOOGLE_CLOUD_LOCATION)
        self.messages: list[dict[str, str]] = []

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def chat(self, messages: list[dict[str, str]]) -> str:
        contents, system_instruction = _to_gemini_contents(self.messages + messages)
        response = await self._client.aio.models.generate_content(
            contents=contents,
            model=self._model,
            config=self._base_config.model_copy(update={"system_instruction": system_instruction}),
        )
        response_text = response.text or ""
        self.messages.extend(messages)
        self.messages.append({"role": "assistant", "content": response_text})
        return response_text

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def structured_chat(self, messages: list[dict[str, str]], response_format: type[T]) -> T:
        contents, system_instruction = _to_gemini_contents(self.messages + messages)
        response = await self._client.aio.models.generate_content(
            contents=contents,
            model=self._model,
            config=self._base_config.model_copy(
                update={
                    "response_mime_type": "application/json",
                    "response_schema": response_format,
                    "system_instruction": system_instruction,
                }
            ),
        )
        parsed = cast(T, response.parsed)
        self.messages.extend(messages)
        self.messages.append({"role": "assistant", "content": parsed.model_dump_json()})
        return parsed


class FastOrBestLLM(Enum):
    FAST = auto()
    BEST = auto()


def create_chatbot(model_name: str, temperature: float = DEFAULT_TEMPERATURE) -> ChatBot:
    """Create a ChatBot for the given model. Callers that genuinely need determinism
    can override the temperature (see DEFAULT_TEMPERATURE comment)."""
    return GeminiChatBot(model_name, temperature)


def create_default_chatbot(fast_or_best: FastOrBestLLM) -> ChatBot:
    """Create a chatbot using the configured fast or best model."""
    if fast_or_best == FastOrBestLLM.BEST:
        return create_chatbot(settings.BEST_LLM_MODEL_NAME)
    return create_chatbot(settings.FAST_LLM_MODEL_NAME)
