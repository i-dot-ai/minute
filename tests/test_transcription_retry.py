from unittest.mock import patch

import pytest
from tenacity import RetryError, retry_if_exception_type

from common.services.transcription_services.retry import transcription_retry


def _retry_with(attempts):
    """Build the shared retry decorator from patched settings, with no backoff so tests stay fast."""
    with patch("common.services.transcription_services.retry.settings") as mock_settings:
        mock_settings.TRANSCRIPTION_RETRY_ATTEMPTS = attempts
        mock_settings.TRANSCRIPTION_RETRY_MIN_WAIT_SECONDS = 0
        mock_settings.TRANSCRIPTION_RETRY_MAX_WAIT_SECONDS = 0
        return transcription_retry(retry_if_exception_type(ValueError))


class TestTranscriptionRetry:
    @pytest.mark.asyncio
    async def test_stops_after_the_configured_number_of_attempts(self):
        calls = 0

        @_retry_with(attempts=3)
        async def always_fails():
            nonlocal calls
            calls += 1
            raise ValueError

        with pytest.raises(RetryError):
            await always_fails()

        assert calls == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_errors_outside_the_adapter_condition(self):
        calls = 0

        @_retry_with(attempts=3)
        async def fails_permanently():
            nonlocal calls
            calls += 1
            raise TypeError

        with pytest.raises(TypeError):
            await fails_permanently()

        assert calls == 1
