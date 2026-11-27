"""The shared Settings model must boot without the Azure Speech secrets."""

import pytest

from common.settings import Settings

REQUIRED = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "minute_db",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "password",
    "APP_URL": "http://localhost",
    "REPO": "minute",
    "AUTH_API_URL": "http://auth",
}


@pytest.fixture
def _clear_azure_speech_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.usefixtures("_clear_azure_speech_env")
def test_settings_boot_without_azure_speech(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.AZURE_SPEECH_KEY is None
    assert settings.AZURE_SPEECH_REGION is None
