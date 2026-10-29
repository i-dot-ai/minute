"""Dependency retries must distinguish temporary outages from invalid inputs."""

import httpx
import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from google.genai.errors import ClientError as GoogleClientError
from openai import APIConnectionError, APIStatusError
from sqlalchemy.exc import IntegrityError, OperationalError

from common.services.errors import is_transient


@pytest.mark.parametrize("status", [400, 401, 403, 404, 408, 409, 429, 500, 503])
def test_provider_status_codes(status):
    request = httpx.Request("POST", "https://provider.test")
    response = httpx.Response(status, request=request)
    errors = [
        httpx.HTTPStatusError("provider failed", request=request, response=response),
        APIStatusError("provider failed", response=response, body=None),
        GoogleClientError(status, {"error": {"message": "provider failed"}}),
    ]
    for error in errors:
        assert is_transient(error) is (status in {408, 409, 429} or status >= 500)


def test_transport_and_database_failures_are_retryable():
    request = httpx.Request("POST", "https://provider.test")
    for error in (
        ConnectionError(),
        TimeoutError(),
        httpx.ReadTimeout("timeout"),
        APIConnectionError(request=request),
        EndpointConnectionError(endpoint_url="https://storage.test"),
        OperationalError("SELECT", None, ConnectionError()),
    ):
        assert is_transient(error), type(error).__name__
    assert not is_transient(IntegrityError("INSERT", None, ValueError()))
    assert not is_transient(ValueError("invalid input"))


@pytest.mark.parametrize(
    ("status", "code", "expected"),
    [(403, "AccessDenied", False), (503, "ServiceUnavailable", True), (400, "Throttling", True)],
)
def test_storage_status_codes(status, code, expected):
    error = ClientError({"ResponseMetadata": {"HTTPStatusCode": status}, "Error": {"Code": code}}, "GetObject")
    assert is_transient(error) is expected
