from enum import Enum, auto
from typing import TypeVar

from google.genai.types import (
    GenerateContentConfig,
)
from pydantic import BaseModel

from common.llm.adapters import BedrockModelAdapter, GeminiModelAdapter, ModelAdapter
from common.settings import get_settings

T = TypeVar("T", bound=BaseModel)

# Gemini 3 models are tuned to run at their default temperature of 1.0. Google warns that
# lowering it can cause looping and degraded reasoning, particularly on the long transcripts
# we send for minute generation. Callers that genuinely need determinism can still pass an
# explicit temperature to create_chatbot.
DEFAULT_TEMPERATURE = 1.0


class ChatBot:
    """A conversation with a model: each call sends the history so far plus the new messages.

    It does not retry: the Temporal activity that calls it does.
    """

    def __init__(self, adapter: ModelAdapter) -> None:
        self.adapter = adapter
        self.messages: list[dict[str, str]] = []

    async def chat(self, messages: list[dict[str, str]]) -> str:
        response = await self.adapter.chat(messages=self.messages + messages)
        self.messages.extend(messages)
        self.messages.append({"role": "assistant", "content": response})
        return response

    async def structured_chat(self, messages: list[dict[str, str]], response_format: type[T]) -> T:
        response = await self.adapter.structured_chat(
            messages=self.messages + messages, response_format=response_format
        )
        self.messages.extend(messages)
        self.messages.append({"role": "assistant", "content": response.model_dump_json()})
        return response


class ModelTier(Enum):
    PRIMARY = auto()  # minute generation and other high-complexity tasks
    LIGHTWEIGHT = auto()  # titles, speakers, citations, AI edits


def create_chatbot(provider: str, model_name: str, temperature: float | None = None) -> ChatBot:
    """A ChatBot for a model on the given provider ("bedrock" or "gemini").

    Leave temperature unset for Claude Sonnet 5.5, which rejects non-default sampling values. Unset on
    Gemini means DEFAULT_TEMPERATURE.
    """
    settings = get_settings()
    if provider == "bedrock":
        adapter: ModelAdapter = BedrockModelAdapter(
            model_id=model_name,
            region=settings.AWS_REGION,
            max_tokens=settings.BEDROCK_MAX_OUTPUT_TOKENS,
            read_timeout_seconds=settings.BEDROCK_READ_TIMEOUT_SECONDS,
            temperature=temperature,
        )
    elif provider == "gemini":
        adapter = GeminiModelAdapter(
            model=model_name,
            generate_content_config=GenerateContentConfig(
                safety_settings=GeminiModelAdapter.no_safety_settings(),
                temperature=DEFAULT_TEMPERATURE if temperature is None else temperature,
            ),
        )
    else:
        msg = f"Unsupported LLM provider: {provider}"
        raise ValueError(msg)
    return ChatBot(adapter)


def get_chatbot(tier: ModelTier) -> ChatBot:
    """A ChatBot for the tier's model on the provider set by LLM_PROVIDER."""
    settings = get_settings()
    primary = tier == ModelTier.PRIMARY
    if settings.LLM_PROVIDER == "gemini":
        model = settings.GEMINI_PRIMARY_MODEL if primary else settings.GEMINI_LIGHTWEIGHT_MODEL
    else:
        model = settings.BEDROCK_PRIMARY_MODEL if primary else settings.BEDROCK_LIGHTWEIGHT_MODEL
    return create_chatbot(settings.LLM_PROVIDER, model)
