import httpx
import pytest
from tenacity import Future, RetryCallState

from workers.transcription.services._helpers import wait_for_retry_after


def _retry_state(exc: Exception, attempt_number: int = 1) -> RetryCallState:
    """Build a minimal RetryCallState whose outcome is a failed call raising `exc`."""
    state = RetryCallState(retry_object=None, fn=None, args=(), kwargs={})
    state.attempt_number = attempt_number
    state.outcome = Future.construct(attempt_number, exc, has_exception=True)
    return state


def _http_429(retry_after: str | None) -> httpx.HTTPStatusError:
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    response = httpx.Response(429, headers=headers)
    return httpx.HTTPStatusError("429", request=httpx.Request("POST", "http://x"), response=response)


def test_numeric_retry_after_is_honoured():
    assert wait_for_retry_after()(_retry_state(_http_429("30"))) == 30.0


def test_retry_after_is_capped_at_max_wait():
    wait = wait_for_retry_after(max_wait=10.0)
    assert wait(_retry_state(_http_429("300"))) == 10.0


def test_http_date_retry_after_is_honoured():
    # Far-future date -> positive delta, capped at default max_wait (60s).
    wait = wait_for_retry_after()
    assert wait(_retry_state(_http_429("Wed, 21 Oct 2099 07:28:00 GMT"))) == 60.0


def test_past_http_date_yields_zero():
    wait = wait_for_retry_after()
    assert wait(_retry_state(_http_429("Wed, 21 Oct 1999 07:28:00 GMT"))) == 0.0


def test_no_retry_after_falls_back_to_exponential():
    # attempt 1 of wait_exponential(multiplier=1) -> 1s
    assert wait_for_retry_after()(_retry_state(_http_429(None))) == 1.0


def test_non_http_error_falls_back_to_exponential():
    assert wait_for_retry_after()(_retry_state(httpx.TimeoutException("boom"))) == 1.0


@pytest.mark.parametrize("bad_header", ["not-a-date", ""])
def test_unparseable_header_falls_back(bad_header):
    # Empty or garbage header -> treated as absent -> exponential fallback.
    assert wait_for_retry_after()(_retry_state(_http_429(bad_header))) == 1.0
