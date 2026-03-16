from __future__ import annotations

import pytest

from evals.summarisation.src.adapter_factory import build_azure_apim_adapter


@pytest.mark.parametrize(
    ("url", "api_version", "token", "key", "expected_error"),
    [
        ("", "2024-01-01", "token", "key", "AZURE_APIM_URL is required"),
        ("https://example.com", "", "token", "key", "AZURE_APIM_API_VERSION is required"),
        ("https://example.com", "2024-01-01", "", "key", "AZURE_APIM_ACCESS_TOKEN is required"),
        ("https://example.com", "2024-01-01", "token", "", "AZURE_APIM_SUBSCRIPTION_KEY is required"),
    ],
)
def test_build_azure_apim_adapter_raises_when_missing_env_var(
    monkeypatch, url, api_version, token, key, expected_error
):
    monkeypatch.setenv("AZURE_APIM_URL", url)
    monkeypatch.setenv("AZURE_APIM_API_VERSION", api_version)
    monkeypatch.setenv("AZURE_APIM_ACCESS_TOKEN", token)
    monkeypatch.setenv("AZURE_APIM_SUBSCRIPTION_KEY", key)

    with pytest.raises(ValueError, match=expected_error):
        build_azure_apim_adapter()


def test_build_azure_apim_adapter_success(monkeypatch):
    base_url = "https://api.example.com/openai/"
    api_version = "2024-02-15-preview"
    model_name = "gpt-4-turbo"

    monkeypatch.setenv("AZURE_APIM_URL", base_url)
    monkeypatch.setenv("AZURE_APIM_API_VERSION", api_version)
    monkeypatch.setenv("AZURE_APIM_ACCESS_TOKEN", "test-access-token-123")
    monkeypatch.setenv("AZURE_APIM_SUBSCRIPTION_KEY", "test-subscription-key-456")
    monkeypatch.setenv("BEST_LLM_MODEL_NAME", model_name)

    adapter = build_azure_apim_adapter()

    assert isinstance(adapter, type(adapter))
    assert adapter._model == model_name  # noqa: SLF001
    assert adapter._api_version == api_version  # noqa: SLF001
    assert adapter.async_apim_client is not None
    assert str(adapter.async_apim_client.base_url).rstrip("/") == f"{base_url.rstrip('/')}/{model_name}"
    assert "Ocp-Apim-Subscription-Key" in adapter.async_apim_client.default_headers
