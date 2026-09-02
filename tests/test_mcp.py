import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime

import httpx2
import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError
from i_dot_ai_utilities.auth.auth_api import UserAuthorisationResult
from sqlalchemy import delete
from sqlmodel import col, select

from backend.main import app, mcp_app
from backend.mcp_server.auth import mcp_session
from common.database.postgres_models import JobStatus, Transcription, User

MCP_URL = "http://test/mcp/"
ANY_TOKEN = "a-token-the-auth-api-will-be-asked-about"  # noqa: S105

DIALOGUE = [
    {"speaker": "Chair", "text": "Welcome to the quarterly procurement review.", "start_time": 0.0, "end_time": 3.0},
    {"speaker": "Analyst", "text": "The framework agreement expires in March.", "start_time": 3.0, "end_time": 6.0},
]


@contextmanager
def auth_api_says(email: str, *, is_authorised: bool = True, unavailable: bool = False):
    """Stand in for the Auth API, which is the only thing that validates a token.

    Tests run with ENVIRONMENT=local, where the real get_user_info short-circuits
    to a single dummy user regardless of the token, so it has to be replaced to
    say anything about who is calling.
    """

    def fake_get_user_info(token: str) -> UserAuthorisationResult:  # noqa: ARG001
        if unavailable:
            error = "Auth API unreachable"
            raise RuntimeError(error)
        return UserAuthorisationResult(email=email, is_authorised=is_authorised, auth_reason="TEST")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("backend.mcp_server.auth.get_user_info", fake_get_user_info)
        yield


@asynccontextmanager
async def users(count: int = 1):
    """Create throwaway users, and remove them and their data afterwards."""
    created = [User(email=f"mcp-test-{uuid.uuid4()}@test.co.uk") for _ in range(count)]
    async with mcp_session() as session:
        for user in created:
            session.add(user)
        await session.commit()

    try:
        yield created[0] if count == 1 else created
    finally:
        user_ids = [user.id for user in created]
        async with mcp_session() as session:
            # Transcriptions do not cascade from the user.
            await session.execute(delete(Transcription).where(col(Transcription.user_id).in_(user_ids)))
            await session.execute(delete(User).where(col(User.id).in_(user_ids)))
            await session.commit()


async def a_transcription(user: User, title: str, created: datetime | None = None) -> Transcription:
    async with mcp_session() as session:
        transcription = Transcription(
            user_id=user.id,
            title=title,
            status=JobStatus.COMPLETED,
            dialogue_entries=DIALOGUE,
        )
        session.add(transcription)
        await session.commit()

        if created is not None:
            # created_datetime has a server default, so it is set after the fact.
            transcription.created_datetime = created
            session.add(transcription)
            await session.commit()

        return transcription


def _asgi_client_factory(headers=None, auth=None, **kwargs):
    """Point the MCP client at the FastAPI app in-process instead of a socket."""
    kwargs.pop("timeout", None)
    return httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app),
        base_url="http://test",
        headers=headers,
        auth=auth,
        **kwargs,
    )


@asynccontextmanager
async def mcp_test_client(token: str = ANY_TOKEN):
    """An MCP client speaking the real protocol to the mounted app over ASGI."""
    transport = StreamableHttpTransport(
        MCP_URL,
        headers={"Authorization": f"Bearer {token}"},
        httpx_client_factory=_asgi_client_factory,
    )
    # The mounted sub-app's lifespan does not run under ASGITransport, and the
    # streamable-HTTP session manager rejects requests before it starts.
    async with mcp_app.lifespan(mcp_app), Client(transport) as client:
        yield client


async def post_raw(token: str | None):
    """A bare JSON-RPC POST, for asserting on the HTTP-level auth response."""
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(MCP_URL, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=headers)


@pytest.mark.asyncio(loop_scope="session")
async def test_a_request_without_a_token_is_refused_and_points_at_the_metadata():
    response = await post_raw(None)

    assert response.status_code == 401
    assert "resource_metadata=" in response.headers["www-authenticate"]


@pytest.mark.asyncio(loop_scope="session")
async def test_a_user_the_auth_api_declines_is_refused():
    with auth_api_says("denied@test.co.uk", is_authorised=False):
        response = await post_raw(ANY_TOKEN)

    assert response.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_an_unavailable_auth_api_refuses_rather_than_admits():
    with auth_api_says("someone@test.co.uk", unavailable=True):
        response = await post_raw(ANY_TOKEN)

    assert response.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_a_first_time_caller_gets_a_user_record():
    email = f"first-time-{uuid.uuid4()}@test.co.uk"

    try:
        with auth_api_says(email):
            async with mcp_test_client() as client:
                result = await client.call_tool("list_transcripts", {})

        assert result.data == []

        async with mcp_session() as session:
            found = await session.exec(select(User).where(col(User.email) == email))
        assert found.first() is not None
    finally:
        async with mcp_session() as session:
            await session.execute(delete(User).where(col(User.email) == email))
            await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_tools_are_advertised():
    async with users() as owner:
        with auth_api_says(owner.email):
            async with mcp_test_client() as client:
                tools = await client.list_tools()

    assert {tool.name for tool in tools} == {"list_transcripts", "get_transcript"}


@pytest.mark.asyncio(loop_scope="session")
async def test_list_returns_only_the_callers_transcripts():
    async with users(2) as (owner, stranger):
        await a_transcription(owner, "Procurement review")
        await a_transcription(stranger, "Estates planning")

        with auth_api_says(owner.email):
            async with mcp_test_client() as client:
                result = await client.call_tool("list_transcripts", {})

    assert [item.title for item in result.data] == ["Procurement review"]


@pytest.mark.asyncio(loop_scope="session")
async def test_list_narrows_to_a_time_range():
    async with users() as owner:
        await a_transcription(owner, "Last year", created=datetime(2025, 1, 15, tzinfo=UTC))
        await a_transcription(owner, "This year", created=datetime(2026, 6, 10, tzinfo=UTC))

        with auth_api_says(owner.email):
            async with mcp_test_client() as client:
                result = await client.call_tool(
                    "list_transcripts",
                    {"start_date": "2026-01-01", "end_date": "2026-12-31"},
                )

    assert [item.title for item in result.data] == ["This year"]


@pytest.mark.asyncio(loop_scope="session")
async def test_a_bare_date_bound_is_read_as_british_time():
    # 23:30 UTC on 9 June is 00:30 on 10 June in British Summer Time, so asking
    # from the 10th must include it. Reading the bound as UTC would drop it.
    async with users() as owner:
        await a_transcription(owner, "Just after midnight", created=datetime(2026, 6, 9, 23, 30, tzinfo=UTC))

        with auth_api_says(owner.email):
            async with mcp_test_client() as client:
                result = await client.call_tool("list_transcripts", {"start_date": "2026-06-10"})

    assert [item.title for item in result.data] == ["Just after midnight"]


@pytest.mark.asyncio(loop_scope="session")
async def test_list_without_bounds_returns_everything():
    async with users() as owner:
        await a_transcription(owner, "Last year", created=datetime(2025, 1, 15, tzinfo=UTC))
        await a_transcription(owner, "This year", created=datetime(2026, 6, 10, tzinfo=UTC))

        with auth_api_says(owner.email):
            async with mcp_test_client() as client:
                result = await client.call_tool("list_transcripts", {})

    assert [item.title for item in result.data] == ["This year", "Last year"]


@pytest.mark.asyncio(loop_scope="session")
async def test_get_transcript_returns_the_dialogue():
    async with users() as owner:
        transcription = await a_transcription(owner, "Procurement review")

        with auth_api_says(owner.email):
            async with mcp_test_client() as client:
                result = await client.call_tool("get_transcript", {"transcription_id": str(transcription.id)})

    assert "Chair: Welcome to the quarterly procurement review." in result.data.transcript
    assert "Analyst: The framework agreement expires in March." in result.data.transcript


@pytest.mark.asyncio(loop_scope="session")
async def test_another_users_transcript_is_not_readable():
    async with users(2) as (owner, stranger):
        transcription = await a_transcription(stranger, "Estates planning")

        with auth_api_says(owner.email):
            async with mcp_test_client() as client:
                with pytest.raises(ToolError, match="belongs to you"):
                    await client.call_tool("get_transcript", {"transcription_id": str(transcription.id)})


@pytest.mark.asyncio(loop_scope="session")
async def test_a_missing_transcript_is_indistinguishable_from_someone_elses():
    async with users() as owner:
        with auth_api_says(owner.email):
            async with mcp_test_client() as client:
                with pytest.raises(ToolError, match="belongs to you"):
                    await client.call_tool("get_transcript", {"transcription_id": str(uuid.uuid4())})
