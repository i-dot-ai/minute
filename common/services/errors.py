"""Classify dependency failures as retryable (transient) or terminal.

Temporal activities own retries, so provider/SDK clients must not retry internally. They raise;
this decides whether the activity should let Temporal retry (transient) or mark the job failed.
"""

import httpx
from botocore.exceptions import BotoCoreError, ClientError

# 408 timeout, 409 conflict, 429 rate limit; everything >= 500 is a server-side failure.
TRANSIENT_STATUS_CODES = frozenset({408, 409, 429})


def _http_status(error: BaseException) -> int | None:
    """The HTTP status carried by a provider SDK error (OpenAI: status_code, Google genai: code)."""
    for attribute in ("status_code", "code"):
        status = getattr(error, attribute, None)
        if isinstance(status, int):
            return status
    return None


def is_transient(error: BaseException) -> bool:
    if isinstance(error, ConnectionError | TimeoutError | httpx.HTTPError | BotoCoreError):
        return True
    if isinstance(error, ClientError):
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        code = error.response.get("Error", {}).get("Code", "")
        return status >= httpx.codes.INTERNAL_SERVER_ERROR or code in {"RequestTimeout", "SlowDown", "Throttling"}
    status = _http_status(error)
    if status is not None:
        return status in TRANSIENT_STATUS_CODES or status >= httpx.codes.INTERNAL_SERVER_ERROR
    # Provider connection errors that carry no status (e.g. OpenAI's APIConnectionError/APITimeoutError).
    return type(error).__name__.endswith(("ConnectionError", "TimeoutError"))
