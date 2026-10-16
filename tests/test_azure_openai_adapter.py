import importlib
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel


class House(BaseModel):
    color: str


class FakeParsedCompletions:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def parse(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.response


@pytest.fixture
def azure_openai_module(monkeypatch):
    required_settings = {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "minute",
        "POSTGRES_USER": "minute",
        "POSTGRES_PASSWORD": "minute",
        "APP_URL": "http://localhost",
        "REPO": "minute",
        "AUTH_API_URL": "http://localhost/auth",
        "TRANSCRIPTION_QUEUE_NAME": "transcription",
        "TRANSCRIPTION_DEADLETTER_QUEUE_NAME": "transcription-dlq",
        "LLM_QUEUE_NAME": "llm",
        "LLM_DEADLETTER_QUEUE_NAME": "llm-dlq",
        "AZURE_SPEECH_KEY": "dummy",
        "AZURE_SPEECH_REGION": "uksouth",
    }
    for key, value in required_settings.items():
        monkeypatch.setenv(key, value)
    return importlib.import_module("common.llm.adapters.azure_openai")


@pytest.mark.asyncio
async def test_structured_chat_returns_parsed_choice(azure_openai_module, monkeypatch) -> None:
    parsed = House(color="red")
    response = SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(parsed=parsed))])
    completions = FakeParsedCompletions(response)
    azure_client_calls = []
    incomplete_checks = []

    def fake_azure_client(**kwargs: Any) -> Any:
        azure_client_calls.append(kwargs)
        return SimpleNamespace(beta=SimpleNamespace(chat=SimpleNamespace(completions=completions)))

    monkeypatch.setattr(azure_openai_module, "AsyncAzureOpenAI", fake_azure_client)
    monkeypatch.setattr(
        azure_openai_module.OpenAIModelAdapter,
        "choice_incomplete",
        staticmethod(lambda choice, completion: incomplete_checks.append((choice, completion))),
    )

    adapter = azure_openai_module.OpenAIModelAdapter(
        model="deployment-name",
        api_key="api-key",
        azure_endpoint="https://example.com",
        azure_deployment="deployment-name",
        temperature=0.0,
    )

    result = await adapter.structured_chat(
        messages=[{"role": "user", "content": "Describe the house"}],
        response_format=House,
    )

    assert azure_client_calls == [
        {
            "azure_endpoint": "https://example.com",
            "api_key": "api-key",
            "api_version": "2024-08-01-preview",
            "azure_deployment": "deployment-name",
        }
    ]
    assert result == parsed
    assert incomplete_checks == [(response.choices[0], response)]
    assert completions.calls == [
        {
            "model": "deployment-name",
            "messages": [{"role": "user", "content": "Describe the house"}],
            "response_format": House,
            "temperature": 0.0,
        }
    ]
