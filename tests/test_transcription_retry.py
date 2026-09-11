from unittest.mock import AsyncMock, patch

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
        always_fails = AsyncMock(side_effect=ValueError)

        with pytest.raises(RetryError):
            await _retry_with(attempts=3)(always_fails)()

        assert always_fails.await_count == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_errors_outside_the_adapter_condition(self):
        fails_permanently = AsyncMock(side_effect=TypeError)

        with pytest.raises(TypeError):
            await _retry_with(attempts=3)(fails_permanently)()

        assert fails_permanently.await_count == 1
