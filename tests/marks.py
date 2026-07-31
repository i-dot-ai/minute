from os import getenv
from pathlib import Path

import pytest

costs_money = pytest.mark.skipif(
    getenv("ALLOW_TESTS_TO_ACCESS_PAID_APIS") != "1",
    reason="Use Env Var ALLOW_TESTS_TO_ACCESS_PAID_APIS=1 to enable this test",
)

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
