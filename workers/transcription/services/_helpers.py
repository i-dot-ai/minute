import email.utils
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from tenacity import RetryCallState, wait_exponential
from tenacity.wait import wait_base

from common.database.postgres_models import DialogueEntry

logger = logging.getLogger(__name__)


class wait_for_retry_after(wait_base):  # noqa: N801  (tenacity strategies are lower_snake by convention)
    """Tenacity wait strategy that honours an HTTP ``Retry-After`` header.

    When the retried exception is an ``httpx.HTTPStatusError`` carrying a
    ``Retry-After`` header (e.g. Azure's 429 responses), wait for exactly that
    long instead of hammering the API on our own schedule. Otherwise fall back
    to exponential backoff.

    ``Retry-After`` may be either a number of seconds or an HTTP date, per
    RFC 9110; both forms are supported.
    """

    def __init__(self, fallback: wait_base | None = None, max_wait: float = 180.0) -> None:
        # Cap the default exponential fallback at max_wait too, so no code path can
        # ever wait longer than max_wait (an uncapped wait_exponential grows without
        # bound: 1, 2, 4, 8, ... 128s).
        self._fallback = fallback or wait_exponential(multiplier=1, max=max_wait)
        self._max_wait = max_wait

    def __call__(self, retry_state: RetryCallState) -> float:
        retry_after = retry_after_seconds(retry_state)
        if retry_after is not None:
            return min(retry_after, self._max_wait)
        # Clamp the fallback too, so a caller-supplied strategy can't exceed max_wait.
        return min(self._fallback(retry_state), self._max_wait)


def retry_after_seconds(retry_state: RetryCallState) -> float | None:
    """Return Azure's suggested ``Retry-After`` delay in seconds, if any.

    Returns ``None`` when the failed attempt did not carry a parseable
    ``Retry-After`` header (in which case callers fall back to their own backoff).
    """
    if retry_state.outcome is None or not retry_state.outcome.failed:
        return None
    exc = retry_state.outcome.exception()
    if not isinstance(exc, httpx.HTTPStatusError):
        return None

    header = exc.response.headers.get("Retry-After")
    if not header:
        return None
    return _parse_retry_after(header)


def log_retry_after(retry_state: RetryCallState) -> None:
    """Tenacity ``before_sleep`` callback: log the delay before each STT retry.

    Surfaces the actual delay chosen and, when the provider supplied one, Azure's
    suggested ``Retry-After`` value so retries are observable in the logs.
    """
    sleep = getattr(retry_state.next_action, "sleep", None)
    suggested = retry_after_seconds(retry_state)
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if suggested is not None:
        logger.info(
            "Retrying STT (attempt %d) after %.1fs; honouring Azure Retry-After of %.1fs (last error: %s)",
            retry_state.attempt_number,
            sleep if sleep is not None else -1.0,
            suggested,
            exc,
        )
    else:
        logger.info(
            "Retrying STT (attempt %d) after %.1fs; no Azure Retry-After header, using backoff (last error: %s)",
            retry_state.attempt_number,
            sleep if sleep is not None else -1.0,
            exc,
        )


def _parse_retry_after(header: str) -> float | None:
    """Parse a Retry-After header (seconds or HTTP-date) into a delay in seconds."""
    # Numeric form: delay in seconds. Tolerate surrounding whitespace.
    stripped = header.strip()
    try:
        seconds = int(stripped)
    except ValueError:
        pass
    else:
        return float(max(seconds, 0))

    # HTTP-date form: wait until that moment. A malformed header is treated as
    # absent so we fall back to exponential backoff rather than crashing.
    try:
        parsed = email.utils.parsedate_to_datetime(stripped)
    except (TypeError, ValueError):
        logger.warning("Could not parse Retry-After header %r; using fallback backoff", header)
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    delta = (parsed - datetime.now(UTC)).total_seconds()
    return max(delta, 0.0)


def get_dialogue_entries(phrases: list[dict[str, Any]]) -> list[DialogueEntry]:
    return [
        DialogueEntry(
            speaker=str(entry["speaker"]),
            text=entry["text"],
            start_time=float(entry["offsetMilliseconds"]) / 1000,
            end_time=(
                float(entry["offsetMilliseconds"])
                + float(entry["durationMilliseconds"])
            ) / 1000,
        )
        for entry in phrases
    ]
