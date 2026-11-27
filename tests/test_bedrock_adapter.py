"""Unit tests for the Bedrock adapter. No network calls: Converse is mocked at _converse."""

# These tests replace the adapter's private Converse seam and inspect its request config.
# ruff: noqa: SLF001

import logging
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from common.llm.adapters.bedrock import (
    STRUCTURED_OUTPUT_TOOL_NAME,
    BedrockModelAdapter,
    StructuredOutputError,
)
from common.llm.client import ChatBot


class House(BaseModel):
    color: str
    bedrooms: int


def _adapter(**kwargs) -> BedrockModelAdapter:
    return BedrockModelAdapter(
        model_id="eu.anthropic.claude-sonnet-5-5",
        region="eu-west-2",
        max_tokens=1000,
        read_timeout_seconds=10,
        **kwargs,
    )


def _response(*content: dict, stop_reason: str = "end_turn") -> dict:
    return {
        "output": {"message": {"role": "assistant", "content": list(content)}},
        "stopReason": stop_reason,
        "usage": {"inputTokens": 10, "outputTokens": 5},
    }


def test_convert_messages_splits_system_merges_roles_and_drops_blanks():
    system, conversation = BedrockModelAdapter.convert_messages(
        [
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "Here is the transcript."},
            {"role": "user", "content": "Summarise it."},
            {"role": "assistant", "content": "   "},
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "A summary."},
            {"role": "system", "content": "Use British English."},
            {"role": "user", "content": "Shorter, please."},
        ]
    )
    assert system == [{"text": "Be brief."}, {"text": "Use British English."}]
    assert conversation == [
        {"role": "user", "content": [{"text": "Here is the transcript."}, {"text": "Summarise it."}]},
        {"role": "assistant", "content": [{"text": "A summary."}]},
        {"role": "user", "content": [{"text": "Shorter, please."}]},
    ]


def test_convert_messages_rejects_unknown_role():
    with pytest.raises(ValueError, match="Invalid role"):
        BedrockModelAdapter.convert_messages([{"role": "tool", "content": "x"}])


def test_temperature_only_sent_when_set():
    assert "temperature" not in _adapter()._inference_config
    assert _adapter(temperature=0.5)._inference_config["temperature"] == 0.5


def test_sdk_does_not_retry():
    assert _adapter()._client_config.retries["total_max_attempts"] == 1


@pytest.mark.asyncio
async def test_chat_joins_text_blocks_and_ignores_others():
    adapter = _adapter()
    adapter._converse = AsyncMock(
        return_value=_response(
            {"reasoningContent": {"reasoningText": {"text": "..."}}}, {"text": "Hello "}, {"text": "world"}
        )
    )
    assert await adapter.chat([{"role": "user", "content": "Hi"}]) == "Hello world"


@pytest.mark.asyncio
async def test_chat_warns_when_max_tokens_reached(caplog):
    adapter = _adapter()
    adapter._converse = AsyncMock(return_value=_response({"text": "Truncated"}, stop_reason="max_tokens"))
    with caplog.at_level(logging.WARNING):
        await adapter.chat([{"role": "user", "content": "Hi"}])
    assert "max output tokens reached" in caplog.text


@pytest.mark.asyncio
async def test_structured_chat_validates_tool_input():
    adapter = _adapter()
    adapter._converse = AsyncMock(
        return_value=_response(
            {"text": "Recording it now."},
            {
                "toolUse": {
                    "toolUseId": "t1",
                    "name": STRUCTURED_OUTPUT_TOOL_NAME,
                    "input": {"color": "red", "bedrooms": 3},
                }
            },
            stop_reason="tool_use",
        )
    )
    result = await adapter.structured_chat([{"role": "user", "content": "A red house, 3 bedrooms"}], House)

    assert result == House(color="red", bedrooms=3)
    tool_config = adapter._converse.await_args.kwargs["tool_config"]
    tool_spec = tool_config["tools"][0]["toolSpec"]
    assert tool_spec["name"] == STRUCTURED_OUTPUT_TOOL_NAME
    assert tool_spec["inputSchema"]["json"] == House.model_json_schema()
    # Claude Sonnet 5.5 rejects forced tool choice, so the tool is offered with auto.
    assert tool_config["toolChoice"] == {"auto": {}}


@pytest.mark.asyncio
async def test_structured_chat_raises_when_model_makes_no_tool_call():
    adapter = _adapter()
    adapter._converse = AsyncMock(return_value=_response({"text": "It is a red house."}))
    with pytest.raises(StructuredOutputError, match="end_turn"):
        await adapter.structured_chat([{"role": "user", "content": "A red house"}], House)


@pytest.mark.asyncio
async def test_converse_request_shape():
    adapter = _adapter()
    client = AsyncMock()
    client.converse.return_value = _response({"text": "ok"})
    session_client = AsyncMock()
    session_client.__aenter__.return_value = client
    adapter._session.client = lambda *_args, **_kwargs: session_client

    await adapter.chat([{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Hi"}])

    client.converse.assert_awaited_once_with(
        modelId="eu.anthropic.claude-sonnet-5-5",
        messages=[{"role": "user", "content": [{"text": "Hi"}]}],
        inferenceConfig={"maxTokens": 1000},
        system=[{"text": "Be brief."}],
    )


@pytest.mark.asyncio
async def test_chatbot_structured_chat_sends_history():
    adapter = AsyncMock()
    adapter.chat.return_value = "First answer"
    adapter.structured_chat.return_value = House(color="red", bedrooms=3)
    chatbot = ChatBot(adapter)

    await chatbot.chat([{"role": "user", "content": "First question"}])
    await chatbot.structured_chat([{"role": "user", "content": "Second question"}], House)

    assert adapter.structured_chat.await_args.kwargs["messages"] == [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "Second question"},
    ]
    assert chatbot.messages[-1] == {"role": "assistant", "content": House(color="red", bedrooms=3).model_dump_json()}
