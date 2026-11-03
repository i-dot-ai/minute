"""Tests for the in-app support form: the Linear client and POST /support/tickets.

Linear is never called for real. Route tests need the docker-compose Postgres (`make run`).
"""

import json

import httpx
import pytest

from backend.api.routes import support
from common.services import linear_client
from common.services.linear_client import LinearError, LinearNotConfiguredError, create_linear_issue
from tests.utils import get_test_client

VALID_TICKET = {"category": "issue", "subject": "Upload keeps failing", "message": "It fails at 50%"}


@pytest.fixture
def linear_settings(monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "lin_api_test")
    monkeypatch.setenv("LINEAR_TEAM_ID", "team-id")
    monkeypatch.setenv("LINEAR_PROJECT_ID", "project-id")


def mock_linear(monkeypatch, response_json, status_code=200):
    """Route the Linear client's httpx calls to a fake handler; returns the captured requests."""
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status_code, json=response_json)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        linear_client.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    return requests


@pytest.mark.asyncio
@pytest.mark.usefixtures("linear_settings")
async def test_create_linear_issue_success(monkeypatch):
    requests = mock_linear(
        monkeypatch, {"data": {"issueCreate": {"success": True, "issue": {"identifier": "MIN-123"}}}}
    )

    assert await create_linear_issue("Title", "Body") == "MIN-123"

    request = requests[0]
    assert request.headers["Authorization"] == "lin_api_test"
    issue_input = json.loads(request.content)["variables"]["input"]
    assert issue_input == {"teamId": "team-id", "projectId": "project-id", "title": "Title", "description": "Body"}


@pytest.mark.asyncio
@pytest.mark.usefixtures("linear_settings")
async def test_create_linear_issue_omits_project_when_not_set(monkeypatch):
    monkeypatch.setenv("LINEAR_PROJECT_ID", "")
    requests = mock_linear(monkeypatch, {"data": {"issueCreate": {"success": True, "issue": {"identifier": "MIN-1"}}}})

    await create_linear_issue("Title", "Body")

    issue_input = json.loads(requests[0].content)["variables"]["input"]
    assert "projectId" not in issue_input


@pytest.mark.asyncio
@pytest.mark.usefixtures("linear_settings")
@pytest.mark.parametrize(
    "response_json",
    [
        {"errors": [{"message": "teamId must be a UUID"}], "data": None},
        {"data": {"issueCreate": {"success": False, "issue": None}}},
    ],
)
async def test_create_linear_issue_raises_on_graphql_failure(monkeypatch, response_json):
    # Linear reports failures with HTTP 200, so the body must be checked
    mock_linear(monkeypatch, response_json)

    with pytest.raises(LinearError):
        await create_linear_issue("Title", "Body")


@pytest.mark.asyncio
@pytest.mark.usefixtures("linear_settings")
async def test_create_linear_issue_raises_on_http_error(monkeypatch):
    mock_linear(monkeypatch, {"error": "unauthorised"}, status_code=401)

    with pytest.raises(httpx.HTTPStatusError):
        await create_linear_issue("Title", "Body")


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["LINEAR_API_KEY", "LINEAR_TEAM_ID"])
async def test_create_linear_issue_not_configured(monkeypatch, linear_settings, missing):  # noqa: ARG001
    monkeypatch.setenv(missing, "")

    with pytest.raises(LinearNotConfiguredError):
        await create_linear_issue("Title", "Body")


@pytest.mark.asyncio(loop_scope="session")
async def test_create_support_ticket_success(monkeypatch):
    calls = []

    async def fake_create(title, description):
        calls.append((title, description))
        return "MIN-123"

    monkeypatch.setattr(support, "create_linear_issue", fake_create)

    async with get_test_client() as ac:
        response = await ac.post("/support/tickets", json=VALID_TICKET, headers={"User-Agent": "test-browser/1.0"})

    assert response.status_code == 200
    assert response.json() == {"reference": "MIN-123"}
    title, description = calls[0]
    assert title == "[Issue] Upload keeps failing"
    assert description.startswith("User id: ")
    assert description.endswith("\n---\nIt fails at 50%")
    for expected in ("Email: ", "Sent: ", " UTC", "Browser: test-browser/1.0"):
        assert expected in description


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    ("error", "expected_status"),
    [(LinearNotConfiguredError(), 503), (LinearError("boom"), 502), (httpx.ConnectTimeout("slow"), 502)],
)
async def test_create_support_ticket_linear_failure(monkeypatch, error, expected_status):
    async def fake_create(*_):
        raise error

    monkeypatch.setattr(support, "create_linear_issue", fake_create)

    async with get_test_client() as ac:
        response = await ac.post("/support/tickets", json=VALID_TICKET)

    assert response.status_code == expected_status


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "changes",
    [
        {"category": "not-a-category"},
        {"subject": ""},
        {"message": ""},
        {"subject": "x" * 201},
        {"message": "x" * 5001},
    ],
)
async def test_create_support_ticket_validation(monkeypatch, changes):
    async def fail_if_called(*_):
        pytest.fail("Linear should not be called for invalid input")

    monkeypatch.setattr(support, "create_linear_issue", fail_if_called)

    async with get_test_client() as ac:
        response = await ac.post("/support/tickets", json={**VALID_TICKET, **changes})

    assert response.status_code == 422
