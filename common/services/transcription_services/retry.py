import httpx
from tenacity import retry, retry_base, retry_if_exception_type, stop_after_attempt, wait_exponential

from common.settings import get_settings

settings = get_settings()

# Transient failures worth retrying for adapters that call their service through httpx directly.
RETRY_ON_HTTPX_ERRORS = retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException))


def transcription_retry(condition: retry_base):
    """Retry a transcription service call with the backoff shared by every adapter.

    Each adapter decides which errors are worth retrying; how many attempts to make and how long to wait between
    them come from the TRANSCRIPTION_RETRY_* settings, so they are tuned in one place.
    """
    return retry(
        retry=condition,
        wait=wait_exponential(
            multiplier=1,
            min=settings.TRANSCRIPTION_RETRY_MIN_WAIT_SECONDS,
            max=settings.TRANSCRIPTION_RETRY_MAX_WAIT_SECONDS,
        ),
        stop=stop_after_attempt(settings.TRANSCRIPTION_RETRY_ATTEMPTS),
    )
