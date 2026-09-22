from os import getenv
from pathlib import Path

import pytest

from common.settings import get_settings

PAID_APIS_FLAG = "ALLOW_TESTS_TO_ACCESS_PAID_APIS"

AZURE_STT_KEYS = ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION")
GEMINI_KEYS = ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION")
# The default stack transcribes with Azure STT and writes minutes with Gemini
DEFAULT_API_KEYS = AZURE_STT_KEYS + GEMINI_KEYS


def costs_money(*api_keys: str) -> pytest.MarkDecorator:
    """Skip unless paid API tests are enabled and every named API key setting has a value."""
    if getenv(PAID_APIS_FLAG) != "1":
        return pytest.mark.skip(reason=f"Use Env Var {PAID_APIS_FLAG}=1 to enable this test")
    settings = get_settings()
    missing = [key for key in api_keys if not getattr(settings, key)]
    return pytest.mark.skipif(bool(missing), reason=f"Set {', '.join(missing)} in .env to enable this test")


ACCEPTANCE_TEST_FLAG = "RUN_ACCEPTANCE_TESTS"
acceptance_test = pytest.mark.skipif(
    getenv(ACCEPTANCE_TEST_FLAG) != "1",
    reason=f"Use Env Var {ACCEPTANCE_TEST_FLAG}=1 to enable this test",
)


def _has_audio_data() -> bool:
    audio_dir = Path(".data/test_audio/normal")
    return audio_dir.is_dir() and any(audio_dir.iterdir())


requires_audio_data = pytest.mark.skipif(
    not _has_audio_data(),
    reason="This test requires audio files in .data/test_audio/normal",
)
