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
        retry_after = self._retry_after_seconds(retry_state)
        if retry_after is not None:
            wait = min(retry_after, self._max_wait)
            logger.info("Honouring Retry-After: waiting %.1fs before retry", wait)
            return wait
        # Clamp the fallback too, so a caller-supplied strategy can't exceed max_wait.
        return min(self._fallback(retry_state), self._max_wait)

    def _retry_after_seconds(self, retry_state: RetryCallState) -> float | None:
        if retry_state.outcome is None or not retry_state.outcome.failed:
            return None
        exc = retry_state.outcome.exception()
        if not isinstance(exc, httpx.HTTPStatusError):
            return None

        header = exc.response.headers.get("Retry-After")
        if not header:
            return None
        return self._parse_retry_after(header)

    @staticmethod
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
