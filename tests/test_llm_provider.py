"""The LLM provider switch. No network calls."""

import pytest

from common.llm import client
from common.llm.client import ModelTier, get_chatbot


@pytest.fixture
def created(monkeypatch):
    """Record which adapter get_chatbot builds, without constructing real SDK clients."""
    calls = []

    class FakeGemini:
        no_safety_settings = staticmethod(list)

        def __init__(self, **kwargs):
            calls.append(("gemini", kwargs["model"]))

    monkeypatch.setattr(client, "BedrockModelAdapter", lambda **kwargs: calls.append(("bedrock", kwargs["model_id"])))
    monkeypatch.setattr(client, "GeminiModelAdapter", FakeGemini)
    return calls


@pytest.mark.parametrize(
    ("provider", "tier", "expected"),
    [
        ("bedrock", ModelTier.PRIMARY, ("bedrock", "bedrock-primary")),
        ("bedrock", ModelTier.LIGHTWEIGHT, ("bedrock", "bedrock-lightweight")),
        ("gemini", ModelTier.PRIMARY, ("gemini", "gemini-primary")),
        ("gemini", ModelTier.LIGHTWEIGHT, ("gemini", "gemini-lightweight")),
    ],
)
def test_get_chatbot_follows_llm_provider(monkeypatch, created, provider, tier, expected):
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("BEDROCK_PRIMARY_MODEL", "bedrock-primary")
    monkeypatch.setenv("BEDROCK_LIGHTWEIGHT_MODEL", "bedrock-lightweight")
    monkeypatch.setenv("GEMINI_PRIMARY_MODEL", "gemini-primary")
    monkeypatch.setenv("GEMINI_LIGHTWEIGHT_MODEL", "gemini-lightweight")
    get_chatbot(tier)
    assert created == [expected]


def test_create_chatbot_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        client.create_chatbot("openai", "gpt")
