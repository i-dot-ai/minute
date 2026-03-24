from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from evals.summarisation.src.dspy_wrapper import DSPyModelAdapterWrapper


@pytest.fixture
def mock_adapter():
    adapter = Mock()
    adapter.chat = AsyncMock(return_value="Test response")
    return adapter


def test_init_sets_model_and_adapter(mock_adapter):
    wrapper = DSPyModelAdapterWrapper(adapter=mock_adapter, model_name="test-model")

    assert wrapper.adapter == mock_adapter
    assert wrapper.model == "test-model"
    assert wrapper.history == []


def test_call_with_prompt_converts_to_messages(mock_adapter):
    wrapper = DSPyModelAdapterWrapper(adapter=mock_adapter, model_name="test-model")

    result = wrapper(prompt="Hello world")

    assert result == ["Test response"]
    mock_adapter.chat.assert_called_once()
    call_args = mock_adapter.chat.call_args[0][0]
    assert call_args == [{"role": "user", "content": "Hello world"}]


def test_call_with_messages_passes_through(mock_adapter):
    wrapper = DSPyModelAdapterWrapper(adapter=mock_adapter, model_name="test-model")
    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"},
    ]

    result = wrapper(messages=messages)

    assert result == ["Test response"]
    mock_adapter.chat.assert_called_once_with(messages)


def test_call_with_neither_prompt_nor_messages_raises(mock_adapter):
    wrapper = DSPyModelAdapterWrapper(adapter=mock_adapter, model_name="test-model")

    with pytest.raises(ValueError, match="Either prompt or messages must be provided"):
        wrapper()


def test_call_records_history(mock_adapter):
    wrapper = DSPyModelAdapterWrapper(adapter=mock_adapter, model_name="test-model")

    wrapper(prompt="First call")
    wrapper(prompt="Second call", temperature=0.5)

    assert len(wrapper.history) == 2
    assert wrapper.history[0]["messages"] == [{"role": "user", "content": "First call"}]
    assert wrapper.history[0]["response"] == "Test response"
    assert wrapper.history[0]["kwargs"] == {}
    assert wrapper.history[1]["kwargs"] == {"temperature": 0.5}


def test_inspect_history_returns_last_n(mock_adapter):
    wrapper = DSPyModelAdapterWrapper(adapter=mock_adapter, model_name="test-model")

    wrapper(prompt="Call 1")
    wrapper(prompt="Call 2")
    wrapper(prompt="Call 3")

    last_two = wrapper.inspect_history(n=2)

    assert len(last_two) == 2
    assert last_two[0]["messages"] == [{"role": "user", "content": "Call 2"}]
    assert last_two[1]["messages"] == [{"role": "user", "content": "Call 3"}]


def test_inspect_history_empty_returns_empty(mock_adapter):
    wrapper = DSPyModelAdapterWrapper(adapter=mock_adapter, model_name="test-model")

    result = wrapper.inspect_history(n=5)

    assert result == []


def test_call_creates_event_loop_if_needed(mock_adapter):
    wrapper = DSPyModelAdapterWrapper(adapter=mock_adapter, model_name="test-model")

    with (
        patch("asyncio.get_event_loop", side_effect=RuntimeError("No loop")),
        patch("asyncio.new_event_loop") as mock_new_loop,
        patch("asyncio.set_event_loop") as mock_set_loop,
    ):
        mock_loop = Mock()
        mock_loop.run_until_complete = Mock(return_value="Test response")
        mock_new_loop.return_value = mock_loop

        result = wrapper(prompt="Test")

        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(mock_loop)
        assert result == ["Test response"]


def test_call_uses_existing_event_loop(mock_adapter):
    wrapper = DSPyModelAdapterWrapper(adapter=mock_adapter, model_name="test-model")

    mock_loop = Mock()
    mock_loop.run_until_complete = Mock(return_value="Test response")

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        result = wrapper(prompt="Test")

        mock_loop.run_until_complete.assert_called_once()
        assert result == ["Test response"]


def test_call_passes_kwargs_to_history_not_adapter(mock_adapter):
    wrapper = DSPyModelAdapterWrapper(adapter=mock_adapter, model_name="test-model")

    wrapper(prompt="Test", temperature=0.7, max_tokens=100)

    mock_adapter.chat.assert_called_once()
    call_args = mock_adapter.chat.call_args
    assert len(call_args[0]) == 1
    assert call_args[1] == {}

    assert wrapper.history[0]["kwargs"] == {"temperature": 0.7, "max_tokens": 100}


def test_multiple_calls_with_different_message_formats(mock_adapter):
    wrapper = DSPyModelAdapterWrapper(adapter=mock_adapter, model_name="test-model")

    wrapper(prompt="Prompt call")
    wrapper(messages=[{"role": "user", "content": "Message call"}])

    assert len(wrapper.history) == 2
    assert wrapper.history[0]["messages"] == [{"role": "user", "content": "Prompt call"}]
    assert wrapper.history[1]["messages"] == [{"role": "user", "content": "Message call"}]
