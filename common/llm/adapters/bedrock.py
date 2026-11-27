import logging
from typing import Any, TypeVar

import aioboto3
from botocore.config import Config
from pydantic import BaseModel

from .base import ModelAdapter, StructuredOutputError

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

STRUCTURED_OUTPUT_TOOL_NAME = "record_response"

# Claude Sonnet 5.5 rejects forced tool use (toolChoice "any"/"tool" returns a 400), so structured_chat
# offers the tool with toolChoice "auto", tells the model to call it, and checks that it did.
STRUCTURED_OUTPUT_INSTRUCTION = (
    f"Give your answer by calling the {STRUCTURED_OUTPUT_TOOL_NAME} tool exactly once. Do not reply with plain text."
)

# Stop reasons that mean Bedrock withheld some or all of the output, so the caller may get partial output.
# Running out of output tokens ("max_tokens") is logged separately.
WITHHELD_STOP_REASONS = frozenset({"content_filtered", "guardrail_intervened"})


class BedrockModelAdapter(ModelAdapter):
    """Calls an Amazon Bedrock model through the Converse API.

    Messages arrive in the OpenAI shape the rest of the app uses ({"role", "content"}) and are
    converted here. The SDK makes a single attempt: Temporal owns retries, and is_transient in
    common/services/errors.py decides which Bedrock errors are worth retrying.
    """

    def __init__(
        self,
        model_id: str,
        region: str | None,
        max_tokens: int,
        read_timeout_seconds: int,
        temperature: float | None = None,
    ) -> None:
        self._model_id = model_id
        self._region = region
        self._inference_config: dict[str, Any] = {"maxTokens": max_tokens}
        if temperature is not None:
            self._inference_config["temperature"] = temperature
        self._client_config = Config(
            retries={"total_max_attempts": 1, "mode": "standard"},
            read_timeout=read_timeout_seconds,
        )
        self._session = aioboto3.Session()

    @staticmethod
    def convert_messages(messages: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """Split OpenAI-style messages into Converse `system` blocks and `messages` turns.

        System messages become system blocks wherever they appear. Blank content is dropped, and
        consecutive turns with the same role are merged, since Converse needs user and assistant
        turns to alternate.
        """
        system: list[dict[str, str]] = []
        conversation: list[dict[str, Any]] = []
        for message in messages:
            role = message["role"]
            content = message.get("content") or ""
            if not content.strip():
                continue
            if role == "system":
                system.append({"text": content})
            elif role in {"user", "assistant"}:
                if conversation and conversation[-1]["role"] == role:
                    conversation[-1]["content"].append({"text": content})
                else:
                    conversation.append({"role": role, "content": [{"text": content}]})
            else:
                msg = f"Invalid role: {role}"
                raise ValueError(msg)
        return system, conversation

    async def _converse(
        self,
        messages: list[dict[str, str]],
        tool_config: dict[str, Any] | None = None,
        extra_system: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        system, conversation = self.convert_messages(messages)
        system += extra_system or []
        request: dict[str, Any] = {
            "modelId": self._model_id,
            "messages": conversation,
            "inferenceConfig": self._inference_config,
        }
        if system:
            request["system"] = system
        if tool_config:
            request["toolConfig"] = tool_config
        async with self._session.client(
            "bedrock-runtime", region_name=self._region, config=self._client_config
        ) as client:
            return await client.converse(**request)

    def _warn_if_incomplete(self, response: dict[str, Any]) -> None:
        stop_reason = response.get("stopReason")
        usage = response.get("usage", {})
        if stop_reason == "max_tokens":
            logger.warning(
                "max output tokens reached: model: %s input_tokens: %s output_tokens: %s",
                self._model_id,
                usage.get("inputTokens"),
                usage.get("outputTokens"),
            )
        elif stop_reason in WITHHELD_STOP_REASONS:
            logger.warning("Bedrock withheld output: model: %s stop_reason: %s", self._model_id, stop_reason)

    @staticmethod
    def _content_blocks(response: dict[str, Any]) -> list[dict[str, Any]]:
        return response.get("output", {}).get("message", {}).get("content", [])

    async def chat(self, messages: list[dict[str, str]]) -> str:
        response = await self._converse(messages)
        self._warn_if_incomplete(response)
        return "".join(block["text"] for block in self._content_blocks(response) if "text" in block)

    async def structured_chat(self, messages: list[dict[str, str]], response_format: type[T]) -> T:
        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": STRUCTURED_OUTPUT_TOOL_NAME,
                        "description": f"Record the response as a {response_format.__name__}.",
                        "inputSchema": {"json": response_format.model_json_schema()},
                    }
                }
            ],
            "toolChoice": {"auto": {}},
        }
        response = await self._converse(
            messages, tool_config=tool_config, extra_system=[{"text": STRUCTURED_OUTPUT_INSTRUCTION}]
        )
        self._warn_if_incomplete(response)
        for block in self._content_blocks(response):
            tool_use = block.get("toolUse")
            if tool_use and tool_use.get("name") == STRUCTURED_OUTPUT_TOOL_NAME:
                return response_format.model_validate(tool_use["input"])
        msg = (
            f"{self._model_id} did not call the {STRUCTURED_OUTPUT_TOOL_NAME} tool "
            f"(stop_reason: {response.get('stopReason')})"
        )
        raise StructuredOutputError(msg)
