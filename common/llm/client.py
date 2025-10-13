from enum import Enum, auto
from typing import TypeVar

from google.genai.types import (
    GenerateContentConfig,
)
from pydantic import BaseModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

from common.llm.adapters import GeminiModelAdapter, ModelAdapter, OpenAIModelAdapter
from common.prompts import get_hallucination_detection_messages
from common.settings import get_settings
from common.types import LLMHallucination

settings = get_settings()
T = TypeVar("T", bound=BaseModel)


class ChatBot:
    """
    Represents an interface for engaging in conversational AI tasks, including general chat,
    structured interactions, and hallucination detection.

    This class provides methods for interacting with an underlying model adapter to perform various
    chat functionalities. It includes support for retry mechanisms to ensure robust performance in
    case of failures, with methods optimized for both general conversation and specific structured
    responses. The hallucination detection method is available for examining the accuracy of responses.

    Attributes:
        adapter (ModelAdapter): The underlying adapter interface that handles communication
            with the conversational model(s).
    """

    def __init__(self, adapter: ModelAdapter) -> None:
        self.adapter = adapter
        self.messages = []

    async def hallucination_check(self) -> list[LLMHallucination]:
        if settings.HALLUCINATION_CHECK:
            return await self.structured_chat(
                messages=get_hallucination_detection_messages(), response_format=list[LLMHallucination]
            )
        return []

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def chat(self, messages: list[dict[str, str]]) -> str:
        response = await self.adapter.chat(messages=self.messages + messages)
        self.messages.extend(messages)
        self.messages.append({"role": "assistant", "content": response})
        return response

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def structured_chat(self, messages: list[dict[str, str]], response_format: type[T]) -> T:
        response = await self.adapter.structured_chat(messages=messages, response_format=response_format)
        self.messages.extend(messages)
        self.messages.append({"role": "assistant", "content": response.model_dump_json()})
        return response


def create_chatbot(model_type: str, model_name: str, temperature: float) -> ChatBot:
    """
    Creates and returns a chatbot instance based on the specified model type and name.

    This function initializes a ChatBot instance by selecting the appropriate model adapter
    based on the provided model type. It supports "openai" and "gemini" model types. Additional
    settings required for model initialization are sourced from application settings or passed
    as keyword arguments. If an unsupported model type is specified, a ValueError is raised.

    Args:
        model_type: A string specifying the type of the model. Supported values are "openai"
            and "gemini".
        model_name: A string indicating the name of the model to be used.
        **kwargs: Additional keyword arguments to be passed to the model api call, if required.

    Returns:
        ChatBot: An instance of the ChatBot class configured with the appropriate model adapter.

    Raises:
        ValueError: If the specified model type is unsupported.
    """
    if model_type == "openai":
        return ChatBot(
            OpenAIModelAdapter(
                model=model_name,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_deployment=settings.AZURE_DEPLOYMENT,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                temperature=temperature,
            )
        )
    elif model_type == "gemini":
        return ChatBot(
            GeminiModelAdapter(
                model=model_name,
                generate_content_config=GenerateContentConfig(
                    safety_settings=GeminiModelAdapter.no_safety_settings(),
                    temperature=temperature,
                ),
            )
        )
    else:
        msg = f"Unsupported model type: {model_type}"
        raise ValueError(msg)


class FastOrBestLLM(Enum):
    FAST = auto()
    BEST = auto()


def create_default_chatbot(fast_or_best: FastOrBestLLM) -> ChatBot:
    """Helper function to create an OpenAI client. Let's replace when we have something like OmegaConf/Hydra.cc to
    instantiate chatbot"""
    if fast_or_best == FastOrBestLLM.BEST:
        return create_chatbot(settings.BEST_LLM_PROVIDER, settings.BEST_LLM_MODEL_NAME, temperature=0.0)
    else:
        return create_chatbot(settings.FAST_LLM_PROVIDER, settings.FAST_LLM_MODEL_NAME, temperature=0.0)
