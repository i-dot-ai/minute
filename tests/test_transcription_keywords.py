import pytest
import pytest_asyncio
from sqlmodel import col, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.dependencies.get_current_user import get_current_user
from backend.main import app
from common.auth import get_user_info
from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, Transcription, User
from tests.utils import get_or_create_user, get_test_client

ENTRY = {"text": "Discussion of supplier selection", "speaker": "A", "start_time": 0, "end_time": 1}


@pytest_asyncio.fixture
async def keyword_transcription():
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        owner = await get_or_create_user(session, get_user_info(None).email.lower())
        transcription = Transcription(
            user_id=owner.id,
            status=JobStatus.COMPLETED,
            dialogue_entries=[ENTRY],
            search_keywords=["procurement"],
            search_keywords_generated=True,
        )
        session.add(transcription)
        await session.commit()
        try:
            yield transcription.id
        finally:
            await session.exec(delete(Transcription).where(col(Transcription.id) == transcription.id))
            await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_keyword_crud_and_manual_edits(keyword_transcription):
    path = f"/transcriptions/{keyword_transcription}"
    keywords_path = f"{path}/keywords"
    async with get_test_client() as client:
        original = await client.get(keywords_path)
        assert original.json() == {"keywords": ["procurement"]}
        assert original.headers["Cache-Control"] == "private, no-store"

        topics = [f"search phrase {index}" for index in range(8)]
        replaced = await client.put(
            keywords_path, json={"keywords": [" Freedom  of information ", "FREEDOM OF INFORMATION", *topics]}
        )
        assert replaced.status_code == 200
        assert replaced.json() == {"keywords": ["Freedom of information", *topics]}
        for invalid in ([" "], ["word\x00word"], ["first\nsecond"]):
            assert (await client.put(keywords_path, json={"keywords": invalid})).status_code == 422

        edited = await client.patch(path, json={"dialogue_entries": [{**ENTRY, "text": "Something else"}]})
        assert edited.status_code == 200
        assert (await client.get(keywords_path)).json() == replaced.json()

        assert (await client.delete(keywords_path)).status_code == 204
        assert (await client.get(keywords_path)).json() == {"keywords": []}
        assert (await client.delete(keywords_path)).status_code == 204


@pytest.mark.asyncio(loop_scope="session")
async def test_keyword_routes_reject_other_users(keyword_transcription, monkeypatch):
    other_user = User(email="other@example.com")
    monkeypatch.setitem(app.dependency_overrides, get_current_user, lambda: other_user)
    path = f"/transcriptions/{keyword_transcription}/keywords"
    async with get_test_client() as client:
        assert (await client.get(path)).status_code == 404
        assert (await client.put(path, json={"keywords": ["new topic"]})).status_code == 404
        assert (await client.delete(path)).status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_transcript_text_edits_clear_generated_keywords(keyword_transcription):
    path = f"/transcriptions/{keyword_transcription}"
    keywords_path = f"{path}/keywords"
    async with get_test_client() as client:
        renamed = await client.patch(
            path, json={"title": "Renamed meeting", "dialogue_entries": [{**ENTRY, "speaker": "Alex"}]}
        )
        assert renamed.status_code == 200
        assert {"search_keywords", "search_keywords_generated"}.isdisjoint(renamed.json())
        assert (await client.get(keywords_path)).json() == {"keywords": ["procurement"]}

        edited = await client.patch(path, json={"dialogue_entries": [{**ENTRY, "text": "Something else"}]})
        assert edited.status_code == 200
        assert (await client.get(keywords_path)).json() == {"keywords": []}
