"""Search helpers and the pilot endpoint against local Postgres; no paid APIs."""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from fastapi import Response
from sqlalchemy import update
from sqlmodel import col, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.routes.transcriptions import search_transcriptions
from backend.utils.transcription_search import search_patterns, search_previews, summary_plain_text
from common.auth import get_user_info
from common.database.postgres_database import async_engine
from common.database.postgres_models import JobStatus, Minute, MinuteVersion, Transcription, User
from common.sentry import _redact_search_query
from common.services.exceptions import MissingAuthTokenError
from common.types import TranscriptionSearchSource
from tests.utils import get_or_create_user, get_test_client


def test_search_queries_are_redacted_from_backend_telemetry():
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1", "GET", "/transcriptions/search?search=private", "1.1", 200),
        None,
    )
    assert logging.getLogger("uvicorn.access").filter(record)
    assert "private" not in record.getMessage()
    event = {"request": {"url": "http://test/transcriptions/search?search=private", "query_string": "search=private"}}
    assert _redact_search_query(event, {})["request"] == {"url": "http://test/transcriptions/search"}


def test_html_extraction_and_literal_utf16_highlights():
    text = summary_plain_text(
        '<h2>😀 R&amp;D</h2><p class="hidden">bud<strong>get</strong> approval</p>'
        "<script>secret</script><style>secret</style><template>secret</template><p>100%_\\</p>"
    )
    assert text == "😀 R&D budget approval 100%_\\"
    matches, truncated = search_previews(iter([("summary", text, {})]), search_patterns("BUD budget approval 100%_\\"))
    assert not truncated
    match = matches[0]
    encoded = match.snippet.encode("utf-16-le")
    assert [encoded[h.start * 2 : h.end * 2].decode("utf-16-le") for h in match.highlights] == [
        "budget",
        "approval",
        "100%_\\",
    ]
    assert match.highlights[0].start == 7


def test_excerpts_are_bounded_and_locate_later_hits():
    text = ("😀 " + "x" * 300 + " budget approval ") * 5
    matches, truncated = search_previews(iter([("transcript", text, {})]), search_patterns("budget approval"))
    assert len(matches) == 3
    assert truncated
    encoded = text.encode("utf-16-le")
    for match in matches:
        assert len(match.snippet) <= 240
        snippet_bytes = match.snippet.encode("utf-16-le")
        assert encoded[match.snippet_start * 2 : match.snippet_start * 2 + len(snippet_bytes)] == snippet_bytes
        assert [snippet_bytes[h.start * 2 : h.end * 2].decode("utf-16-le") for h in match.highlights] == [
            "budget",
            "approval",
        ]
    dense, truncated = search_previews(iter([("transcript", "budget" * 1_000, {})]), search_patterns("budget"))
    assert truncated
    assert len(dense) == 3
    assert all(len(match.snippet) == 240 for match in dense)
    overlapping, truncated = search_previews(iter([("transcript", "ab" * 1_000, {})]), search_patterns("aba bab"))
    assert truncated
    assert all(len(match.snippet) <= 243 for match in overlapping)


@pytest.mark.asyncio
@pytest.mark.parametrize("page_size", [1, 2, 3])
@pytest.mark.parametrize(
    ("sources", "search", "expected_indices", "deleted_index"),
    [
        (tuple(TranscriptionSearchSource), "budget", (3, 7, 2, 6, 1, 5, 0, 4), None),
        ((TranscriptionSearchSource.TRANSCRIPT,), "budget", (0, 4, 7), None),
        ((TranscriptionSearchSource.TRANSCRIPT, TranscriptionSearchSource.SUMMARY), "budget", (1, 5, 7, 0, 4), None),
        (tuple(TranscriptionSearchSource), "absent", (), None),
        (tuple(TranscriptionSearchSource), "budget", (3, 7, 2, 6, 1, 5, 0, 4), 7),
    ],
)
async def test_search_ranks_sources_before_date_and_paginates(
    monkeypatch, page_size, sources, search, expected_indices, deleted_index
):
    monkeypatch.setattr("backend.api.routes.transcriptions.SEARCH_BATCH_SIZE", 2)
    previews = Mock(wraps=search_previews)
    monkeypatch.setattr("backend.api.routes.transcriptions.search_previews", previews)
    now = datetime.now(UTC)
    rows = []
    # Newer transcript matches must rank below older title, speaker and summary matches.
    for index, source in enumerate(("transcript", "summary", "speaker", "title") * 2):
        multiple_sources = index == 7
        row = Transcription(
            title="Budget" if source == "title" else "Unrelated",
            status=JobStatus.COMPLETED,
            created_datetime=now - timedelta(minutes=index),
            dialogue_entries=[
                {
                    "speaker": "Budget" if source == "speaker" or multiple_sources else "Alex",
                    "text": "Budget" if source == "transcript" or multiple_sources else "Unrelated",
                    "start_time": 0,
                    "end_time": 1,
                }
            ],
        )
        row.minutes = []
        if source == "summary" or multiple_sources:
            minute = Minute(transcription_id=row.id)
            minute.minute_versions = [
                MinuteVersion(
                    minute_id=minute.id,
                    html_content="<p>Budget</p>",
                    status=JobStatus.COMPLETED,
                    created_datetime=now,
                )
            ]
            row.minutes = [minute]
        rows.append(row)

    batches = [rows[index : index + 2] for index in range(0, len(rows), 2)] + [[]]
    expected = [rows[index].id for index in expected_indices]
    deleted_id = rows[deleted_index].id if deleted_index is not None else None
    total_pages = (len(expected) + page_size - 1) // page_size or 1
    for page in range(1, total_pages + 2):
        previews.reset_mock()
        expected_page = expected[(page - 1) * page_size : page * page_size]
        # The page fetch returns date order, which can differ from source rank order.
        page_rows = [row for row in rows if row.id in expected_page and row.id != deleted_id]
        results = batches + ([page_rows] if expected_page else [])
        session = SimpleNamespace(exec=AsyncMock(side_effect=[SimpleNamespace(all=lambda b=b: b) for b in results]))
        user = User(data_retention_days=None)
        response = await search_transcriptions(
            session, user, Response(), search=search, page=page, page_size=page_size, sources=sources
        )
        assert response.total_count == len(expected)
        assert response.total_pages == total_pages
        assert [item.id for item in response.items] == [item_id for item_id in expected_page if item_id != deleted_id]
        assert previews.call_count == len(page_rows)
        assert session.exec.await_count == len(results)
        if expected_page:
            parameters = session.exec.call_args.args[0].compile().params
            assert parameters["id_1"] == expected_page
            assert parameters["user_id_1"] == user.id
        for item in response.items:
            if item.id == rows[7].id:
                assert [match.source for match in item.matches] == [
                    source for source in ("title", "speaker", "summary", "transcript") if source in sources
                ]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    ("source", "key"),
    [(TranscriptionSearchSource.TITLE, "title"), (TranscriptionSearchSource.SUMMARY, "history")],
)
async def test_search_omits_rows_edited_after_matching(searchable, monkeypatch, source, key):
    token, rows, versions = searchable
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        # Keep the scanned object alive so the page query must refresh it.
        transcription = await session.get(Transcription, rows[key].id)
        user = await session.get(User, transcription.user_id)
        exec_query = session.exec

        async def exec_with_edit(statement):
            if "id_1" in statement.compile().params:
                # Commit the edit from another session just before fetching the page.
                async with AsyncSession(async_engine) as writer:
                    if source == TranscriptionSearchSource.TITLE:
                        await writer.exec(
                            update(Transcription).where(Transcription.id == transcription.id).values(title="Changed")
                        )
                    else:
                        await writer.exec(
                            delete(MinuteVersion).where(MinuteVersion.minute_id == versions[key][0].minute_id)
                        )
                    await writer.commit()
            return await exec_query(statement)

        monkeypatch.setattr(session, "exec", exec_with_edit)
        response = await search_transcriptions(session, user, Response(), search=f"{token} approval", sources=(source,))

    assert response.total_count == 1
    assert response.total_pages == 1
    assert response.items == []


@pytest_asyncio.fixture
async def searchable():
    token = f"searchtest{uuid.uuid4().hex}"
    rows = {}
    now = datetime.now(UTC)
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        own = await get_or_create_user(session, get_user_info(None).email.lower())
        foreign = User(email=f"{token}@example.com")
        session.add(foreign)
        await session.flush()
        specifications = [
            ("title", own.id, JobStatus.FAILED, f"{token} approval", []),
            ("transcript", own.id, JobStatus.COMPLETED, "Unrelated", [f"😀 {token}", "Approval"]),
            ("history", own.id, JobStatus.COMPLETED, "Unrelated", []),
            ("cross_source", own.id, JobStatus.COMPLETED, token, ["approval"]),
            ("cross_version", own.id, JobStatus.COMPLETED, "Unrelated", []),
            ("html_only", own.id, JobStatus.COMPLETED, "Unrelated", []),
            ("processing", own.id, JobStatus.IN_PROGRESS, "Unrelated", [f"{token} approval"]),
            ("foreign", foreign.id, JobStatus.COMPLETED, f"{token} approval", [f"{token} approval"]),
            ("speaker", own.id, JobStatus.COMPLETED, "Unrelated", ["Discussed the next steps."] * 4),
            ("split_speakers", own.id, JobStatus.COMPLETED, "Unrelated", ["Nothing relevant."] * 2),
        ]
        for index, (key, user_id, status, title, entries) in enumerate(specifications):
            row = Transcription(
                user_id=user_id,
                status=status,
                title=title,
                created_datetime=now - timedelta(minutes=index),
                dialogue_entries=[
                    {"text": text, "speaker": "Alex", "start_time": float(i), "end_time": float(i + 1)}
                    for i, text in enumerate(entries)
                ],
            )
            rows[key] = row
            session.add(row)
        rows["speaker"].dialogue_entries = [
            {**entry, "speaker": f"Alex {token}"} for entry in rows["speaker"].dialogue_entries
        ]
        rows["split_speakers"].dialogue_entries = [
            {**entry, "speaker": name}
            for entry, name in zip(rows["split_speakers"].dialogue_entries, ("Alex", token), strict=True)
        ]
        rows["foreign"].dialogue_entries = [
            {**entry, "speaker": f"Alex {token}"} for entry in rows["foreign"].dialogue_entries
        ]
        await session.flush()
        versions = {}
        for key, bodies in {
            "history": [f"<p>{token} approval</p>"] * 4 + ["<p>No longer mentioned</p>"],
            "cross_version": [f"<p>{token}</p>", "<p>approval</p>"],
            "html_only": [f'<p class="{token}">approval</p><script>{token}</script>'],
            "processing": [f"<p>{token} approval</p>"],
            "foreign": [f"<p>{token} approval</p>"],
        }.items():
            minute = Minute(transcription_id=rows[key].id)
            session.add(minute)
            await session.flush()
            versions[key] = []
            for index, html in enumerate(bodies):
                version = MinuteVersion(
                    minute_id=minute.id,
                    html_content=html,
                    status=JobStatus.IN_PROGRESS if key == "processing" else JobStatus.COMPLETED,
                    created_datetime=now + timedelta(seconds=index),
                )
                versions[key].append(version)
                session.add(version)
        await session.commit()
    try:
        yield token, rows, versions
    finally:
        async with AsyncSession(async_engine) as session:
            await session.exec(
                delete(Transcription).where(col(Transcription.id).in_([row.id for row in rows.values()]))
            )
            await session.exec(delete(User).where(User.id == foreign.id))
            await session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_search_ownership_sources_history_and_pagination(searchable, monkeypatch):
    token, rows, versions = searchable
    # Exercise crossing candidate batches before filtering and paginating matches.
    monkeypatch.setattr("backend.api.routes.transcriptions.SEARCH_BATCH_SIZE", 2)
    async with get_test_client() as client:
        params = {
            "search": f"  {token.upper()} approval {token} ",
            "page_size": 2,
            "user_id": str(rows["foreign"].user_id),
        }
        response = await client.get("/transcriptions/search", params=params)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "private, no-store"
        body = response.json()
        assert body["total_count"] == 3
        assert body["total_pages"] == 2
        assert [item["id"] for item in body["items"]] == [str(rows[key].id) for key in ("title", "history")]
        assert body["items"][0]["matches"][0]["source"] == "title"

        second = (await client.get("/transcriptions/search", params={**params, "page": 2})).json()
        assert second["total_count"] == 3
        assert second["items"][0]["id"] == str(rows["transcript"].id)
        transcript_matches = second["items"][0]["matches"]
        assert [match["entry_index"] for match in transcript_matches] == [0, 1]
        assert transcript_matches[0]["speaker"] == "Alex"
        assert transcript_matches[0]["start_time"] == 0.0
        assert transcript_matches[0]["highlights"] == [{"start": 3, "end": 3 + len(token)}]
        item = body["items"][1]
        assert item["id"] == str(rows["history"].id)
        assert item["matches_truncated"]
        assert [match["minute_version_id"] for match in item["matches"]] == [
            str(version.id) for version in reversed(versions["history"][1:4])
        ]
        assert all(match["minute_id"] == str(versions["history"][0].minute_id) for match in item["matches"])

        failed = (await client.get("/transcriptions/search", params={**params, "filter_by": "failed"})).json()
        assert failed["total_count"] == 1
        assert failed["items"][0]["id"] == str(rows["title"].id)

        for source, key in (("title", "title"), ("transcript", "transcript"), ("summary", "history")):
            scoped = await client.get("/transcriptions/search", params={**params, "sources": source})
            assert scoped.status_code == 200
            assert scoped.json()["total_count"] == 1
            assert scoped.json()["items"][0]["id"] == str(rows[key].id)
            assert all(match["source"] == source for match in scoped.json()["items"][0]["matches"])
        combined = await client.get("/transcriptions/search", params={**params, "sources": ["transcript", "summary"]})
        assert combined.json()["total_count"] == 2
        assert [item["id"] for item in combined.json()["items"]] == [
            str(rows[key].id) for key in ("history", "transcript")
        ]

        speaker_query = {"search": f"alex {token.upper()}", "sources": "speaker"}
        speakers = await client.get("/transcriptions/search", params=speaker_query)
        assert speakers.status_code == 200
        assert speakers.json()["total_count"] == 1
        speaker = speakers.json()["items"][0]
        assert speaker["id"] == str(rows["speaker"].id)
        assert len(speaker["matches"]) == 1  # Repeated turns from the same speaker are collapsed.
        match = speaker["matches"][0]
        assert match["snippet"] == f"Alex {token}"
        assert match["highlights"] == [{"start": 0, "end": 4}, {"start": 5, "end": 5 + len(token)}]
        assert match["speech_excerpt"] == "Discussed the next steps."
        assert match["entry_index"] == 0
        assert (await client.get("/transcriptions/search", params={"search": speaker_query["search"]})).json()[
            "total_count"
        ] == 1

        # The old endpoint remains title-only, despite a matching transcript and history.
        old = (await client.get("/transcriptions", params={"search": token})).json()
        assert {item["id"] for item in old["items"]} == {str(rows[key].id) for key in ("title", "cross_source")}

        # Existing edit paths are immediately reflected without a search backfill.
        edited = await client.patch(
            f"/transcriptions/{rows['transcript'].id}",
            json={"dialogue_entries": [{"text": "Changed", "speaker": "Alex", "start_time": 0, "end_time": 1}]},
        )
        assert edited.status_code == 200
        assert (await client.get("/transcriptions/search", params=params)).json()["total_count"] == 2


@pytest.mark.asyncio(loop_scope="session")
async def test_search_validation_and_empty_results(monkeypatch):
    async with get_test_client() as client:
        for params in (
            {},
            {"search": " "},
            {"search": "x" * 101},
            {"search": "x", "page_size": 101},
            {"search": "x", "sources": ""},
            {"search": "x", "sources": "unknown"},
        ):
            assert (await client.get("/transcriptions/search", params=params)).status_code == 422
        response = await client.get("/transcriptions/search", params={"search": uuid.uuid4().hex})
        assert response.status_code == 200
        assert response.json() == {"items": [], "total_count": 0, "total_pages": 1, "page": 1, "page_size": 20}

        def unauthenticated(_token):
            raise MissingAuthTokenError

        monkeypatch.setattr("backend.api.dependencies.get_current_user.get_user_info", unauthenticated)
        assert (await client.get("/transcriptions/search", params={"search": "private"})).status_code == 401
