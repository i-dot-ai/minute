"""Classify dependency failures as retryable (transient) or terminal.

Temporal activities own retries, so provider/SDK clients must not retry internally. They raise;
this decides whether the activity should let Temporal retry (transient) or mark the job failed.
"""

import httpx
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import DBAPIError, DisconnectionError, InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as DatabaseTimeoutError

# 408 timeout, 409 conflict, 429 rate limit; everything >= 500 is a server-side failure.
TRANSIENT_STATUS_CODES = frozenset({408, 409, 429})

# AWS error codes worth retrying whatever HTTP status they arrive with: S3 throttling and timeouts, and
# Bedrock throttling, capacity and model start-up errors.
TRANSIENT_AWS_ERROR_CODES = frozenset(
    {
        "RequestTimeout",
        "SlowDown",
        "Throttling",
        "ThrottlingException",
        "ServiceUnavailableException",
        "ModelNotReadyException",
        "ModelTimeoutException",
    }
)


def _http_status(error: BaseException) -> int | None:
    """The HTTP status carried by an httpx error, or by an SDK error exposing status_code or code (Google genai)."""
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code
    for attribute in ("status_code", "code"):
        status = getattr(error, attribute, None)
        if isinstance(status, int):
            return status
    return None


def is_transient(error: BaseException) -> bool:
    status = _http_status(error)
    if status is not None:
        return status in TRANSIENT_STATUS_CODES or status >= httpx.codes.INTERNAL_SERVER_ERROR
    if isinstance(
        error,
        ConnectionError
        | TimeoutError
        | httpx.TransportError
        | BotoCoreError
        | OperationalError
        | InterfaceError
        | DisconnectionError
        | DatabaseTimeoutError,
    ):
        return True
    if isinstance(error, DBAPIError) and error.connection_invalidated:
        return True
    if isinstance(error, ClientError):
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        code = error.response.get("Error", {}).get("Code", "")
        return (
            status in TRANSIENT_STATUS_CODES
            or status >= httpx.codes.INTERNAL_SERVER_ERROR
            or code in TRANSIENT_AWS_ERROR_CODES
        )
    # Connection errors from other clients that carry no status, named like the builtin exceptions.
    return type(error).__name__.endswith(("ConnectionError", "TimeoutError"))
