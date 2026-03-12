from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from jinja2 import Environment, TemplateNotFound
from evals.dataset_generation.transcription_generation.src.constants import (get_template, PROMPTS_DIR, ACTOR_GENERATOR_TEMPLATE)
from common.llm.client import ChatBot
import pytest

@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.chat = AsyncMock(return_value="default response")
    adapter.structured_chat = AsyncMock()
    return adapter


@pytest.mark.asyncio
async def test_message_history_structure(mock_adapter):
    mock_adapter.chat = AsyncMock(side_effect=["Response 1", "Response 2", "Response 3"])
    chatbot = ChatBot(adapter=mock_adapter)

    await chatbot.chat(messages=[{"role": "user", "content": "Hello"}])
    await chatbot.chat(messages=[{"role": "user", "content": "How are you?"}])
    await chatbot.chat(messages=[{"role": "user", "content": "Tell me a joke"}])

    expected = [
        {"role": "user",      "content": "Hello"},
        {"role": "assistant", "content": "Response 1"},
        {"role": "user",      "content": "How are you?"},
        {"role": "assistant", "content": "Response 2"},
        {"role": "user",      "content": "Tell me a joke"},
        {"role": "assistant", "content": "Response 3"},
    ]
    assert chatbot.messages == expected

@pytest.mark.asyncio
async def test_chat_appends_to_message_history(mock_adapter):
    mock_adapter.chat = AsyncMock(side_effect=[
        "Hello, I am an AI.",
        "Second response",
        "Third response"
    ])
    chatbot = ChatBot(adapter=mock_adapter)

    await chatbot.chat(messages=[{"role": "user", "content": "Hi"}])

    expected = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello, I am an AI."},
    ]

    assert chatbot.messages == expected
