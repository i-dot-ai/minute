"""Tests for the paginated GET /transcriptions endpoint.

Rows are seeded straight into Postgres rather than through POST /transcriptions,
which would queue real transcription work. Every seeded title carries a unique
token so the assertions can scope themselves with ?search= and stay correct
against a dev database that already holds other transcriptions.

Requires the docker-compose Postgres (`make run`).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlmodel import col, delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from common.auth import get_user_info
from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, Transcription, User
from tests.utils import get_test_client

# Recent enough that the rows never fall the wrong side of a retention cutoff,
# whatever data_retention_days the dev user happens to have.
SEED_TIME = datetime.now(UTC) - timedelta(minutes=10)


async def _current_user_id(session: AsyncSession) -> uuid.UUID:
    """The user the test client authenticates as (dummy local-auth user)."""
    email = get_user_info(None).email.lower()
    user = (await session.exec(select(User).where(User.email == email))).first()
    if user is None:
        user = User(email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user.id


async def _seed(token: str, rows: list[tuple[JobStatus, datetime]]) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        user_id = await _current_user_id(session)
        for index, (status, created) in enumerate(rows):
            transcription = Transcription(
                user_id=user_id,
                title=f"{token} meeting {index}",
                status=status,
                created_datetime=created,
                dialogue_entries=[{"speaker": "A", "text": f"body {index}", "start_time": 0.0, "end_time": 1.0}],
            )
            session.add(transcription)
            ids.append(transcription.id)
        await session.commit()
    return ids


async def _delete(ids: list[uuid.UUID]) -> None:
    async with AsyncSession(async_engine) as session:
        await session.exec(delete(Transcription).where(col(Transcription.id).in_(ids)))
        await session.commit()


@pytest_asyncio.fixture
async def seeded():
    """Three transcriptions sharing a unique title token; yields (token, ids)."""
    token = f"listtest{uuid.uuid4().hex[:8]}"
    # Spaced timestamps so the newest-first ordering is assertable.
    ids = await _seed(
        token,
        [
            (JobStatus.COMPLETED, SEED_TIME),
            (JobStatus.COMPLETED, SEED_TIME + timedelta(minutes=1)),
            (JobStatus.FAILED, SEED_TIME + timedelta(minutes=2)),
        ],
    )
    yield token, ids
    await _delete(ids)


@pytest_asyncio.fixture
async def seeded_old():
    """A single transcription old enough to sit beyond any retention cutoff."""
    token = f"listtest{uuid.uuid4().hex[:8]}"
    ids = await _seed(token, [(JobStatus.COMPLETED, datetime(2024, 1, 1, 12, 0, tzinfo=UTC))])
    yield token, ids
    await _delete(ids)


@pytest.mark.asyncio(loop_scope="session")
async def test_list_transcriptions_paginates(seeded):
    token, ids = seeded
    async with get_test_client() as ac:
        first = await ac.get("/transcriptions", params={"search": token, "page_size": 2})
        assert first.status_code == 200
        body = first.json()
        assert body["total_count"] == 3
        assert body["total_pages"] == 2
        assert body["page"] == 1
        assert body["page_size"] == 2
        # Newest first: index 2 was created last.
        assert [item["title"] for item in body["items"]] == [f"{token} meeting 2", f"{token} meeting 1"]

        second = await ac.get("/transcriptions", params={"search": token, "page_size": 2, "page": 2})
        assert second.status_code == 200
        body = second.json()
        assert body["total_count"] == 3
        assert body["page"] == 2
        assert [item["title"] for item in body["items"]] == [f"{token} meeting 0"]
        assert {uuid.UUID(item["id"]) for item in body["items"]} <= set(ids)


@pytest.mark.asyncio(loop_scope="session")
async def test_list_transcriptions_returns_metadata(seeded):
    token, _ = seeded
    async with get_test_client() as ac:
        response = await ac.get("/transcriptions", params={"search": token, "page_size": 1})
        item = response.json()["items"][0]
        assert item["text"] == "body 2"
        assert item["status"] == JobStatus.FAILED
        assert item["expiring"] is False


@pytest.mark.asyncio(loop_scope="session")
async def test_list_transcriptions_marks_old_rows_expiring(seeded_old):
    """A row older than the retention cutoff is flagged, and the expiring-soon filter finds it."""
    token, _ = seeded_old
    async with get_test_client() as ac:
        original = (await ac.get("/users/me")).json()["data_retention_days"]
        await ac.patch("/users/data-retention", json={"data_retention_days": 30})
        try:
            response = await ac.get("/transcriptions", params={"search": token, "filter_by": "expiring-soon"})
            body = response.json()
            assert body["total_count"] == 1
            assert body["items"][0]["expiring"] is True
        finally:
            await ac.patch("/users/data-retention", json={"data_retention_days": original})


@pytest.mark.asyncio(loop_scope="session")
async def test_list_transcriptions_filters_by_failed(seeded):
    token, _ = seeded
    async with get_test_client() as ac:
        response = await ac.get("/transcriptions", params={"search": token, "filter_by": "failed"})
        body = response.json()
        assert body["total_count"] == 1
        assert body["items"][0]["status"] == JobStatus.FAILED


@pytest.mark.asyncio(loop_scope="session")
async def test_list_transcriptions_empty_result():
    """A count over no matching rows is 0, and an empty list still reports one page."""
    async with get_test_client() as ac:
        response = await ac.get("/transcriptions", params={"search": f"nomatch{uuid.uuid4().hex}"})
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total_count"] == 0
        assert body["total_pages"] == 1
