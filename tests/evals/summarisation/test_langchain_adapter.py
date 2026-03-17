from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from evals.summarisation.src.langchain_adapter import (
    LangChainModelAdapter,
    _convert_message_to_dict,
)


@pytest.fixture
def mock_adapter():
    adapter = Mock()
    adapter.chat = AsyncMock(return_value="Test response from LLM")
    return adapter


def test_convert_message_to_dict_human_message():
    msg = HumanMessage(content="Hello")
    result = _convert_message_to_dict(msg)
    assert result == {"role": "user", "content": "Hello"}


def test_convert_message_to_dict_system_message():
    msg = SystemMessage(content="You are helpful")
    result = _convert_message_to_dict(msg)
    assert result == {"role": "system", "content": "You are helpful"}


def test_convert_message_to_dict_ai_message():
    msg = AIMessage(content="I can help")
    result = _convert_message_to_dict(msg)
    assert result == {"role": "ai", "content": "I can help"}


def test_init_sets_adapter_and_model_name(mock_adapter):
    adapter = LangChainModelAdapter(adapter=mock_adapter, model_name="gpt-4")

    assert adapter.adapter == mock_adapter
    assert adapter.model_name == "gpt-4"


def test_invoke_converts_messages_and_calls_adapter(mock_adapter):
    adapter = LangChainModelAdapter(adapter=mock_adapter, model_name="test-model")
    messages = [
        SystemMessage(content="You are helpful"),
        HumanMessage(content="Hello"),
    ]

    result = adapter.invoke(messages)

    mock_adapter.chat.assert_called_once_with(
        [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
    )
    assert isinstance(result, AIMessage)
    assert result.content == "Test response from LLM"


def test_invoke_uses_existing_event_loop(mock_adapter):
    adapter = LangChainModelAdapter(adapter=mock_adapter, model_name="test-model")
    messages = [HumanMessage(content="Test")]

    mock_loop = Mock()
    mock_loop.run_until_complete = Mock(return_value="Test response from LLM")

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        result = adapter.invoke(messages)

        mock_loop.run_until_complete.assert_called_once()
        assert result.content == "Test response from LLM"


def test_invoke_creates_event_loop_if_needed(mock_adapter):
    adapter = LangChainModelAdapter(adapter=mock_adapter, model_name="test-model")
    messages = [HumanMessage(content="Test")]

    mock_loop = Mock()
    mock_loop.run_until_complete = Mock(return_value="Test response from LLM")

    with (
        patch("asyncio.get_event_loop", side_effect=RuntimeError("No loop")),
        patch("asyncio.new_event_loop", return_value=mock_loop),
        patch("asyncio.set_event_loop") as mock_set_loop,
    ):
        result = adapter.invoke(messages)

        mock_set_loop.assert_called_once_with(mock_loop)
        mock_loop.run_until_complete.assert_called_once()
        assert result.content == "Test response from LLM"


def test_invoke_multiple_message_types(mock_adapter):
    adapter = LangChainModelAdapter(adapter=mock_adapter, model_name="test-model")
    messages = [
        SystemMessage(content="You are a math tutor"),
        HumanMessage(content="What is 2+2?"),
        AIMessage(content="4"),
        HumanMessage(content="What is 3+3?"),
    ]

    result = adapter.invoke(messages)

    expected_dicts = [
        {"role": "system", "content": "You are a math tutor"},
        {"role": "user", "content": "What is 2+2?"},
        {"role": "ai", "content": "4"},
        {"role": "user", "content": "What is 3+3?"},
    ]
    mock_adapter.chat.assert_called_once_with(expected_dicts)
    assert result.content == "Test response from LLM"
