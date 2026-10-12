"""End-to-end tests for the single worker queue.

Storage and queues are served by MiniStack, so these never touch dev AWS. The worker
downloads recordings from MiniStack and sends their bytes to synchronous Azure Speech.
"""

import asyncio
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
import pytest_asyncio
import requests

from common.database.postgres_models import ContentSource, JobStatus, Minute, MinuteVersion, Transcription
from common.services.messaging import SQS
from common.settings import get_settings
from common.types import (
    AgendaUsage,
    AiEdit,
    MinutesCreateRequest,
    MinuteVersionCreateRequest,
    RecordingCreateRequest,
    TranscriptionCreateRequest,
)
from tests.marks import costs_money, requires_audio_data
from tests.utils import FileTypeTests, get_test_client
from worker.consumer import Consumer
from worker.signal_handler import SignalHandler
from worker.templates import TEMPLATES
from worker.workflows import generate_minute_version as workflow

pytestmark = [costs_money]


@pytest_asyncio.fixture(autouse=True)
async def worker_queue():
    settings = get_settings()
    queue_service = SQS(settings.WORKER_QUEUE_NAME, settings.WORKER_DEADLETTER_QUEUE_NAME)
    queue_service.purge_messages()
    # needed to ensure sqs queue is purged (not sure if this long is needed for ministack)
    await asyncio.sleep(1)
    return queue_service


async def load_db_test_instance(file_type: FileTypeTests) -> set[UUID]:
    # Note, needs MP3 files at the specified location. Keep them under the
    # Azure synchronous duration limit.
    async with get_test_client() as ac:
        test_audio_dir = Path(".data").joinpath("test_audio").joinpath(file_type.value)
        test_ids = set()
        for test_file in test_audio_dir.iterdir():
            request = RecordingCreateRequest(file_extension="mp3")
            response = await ac.post("/recordings", json=request.model_dump(mode="json"))
            assert response.status_code == 200, f"failed to create recording for  {request.model_dump_json()}"
            response_json = response.json()
            with test_file.open("rb") as f:
                http_response = requests.put(response_json["upload_url"], data=f.read(), timeout=60)  # noqa: ASYNC210
                assert http_response.status_code == 200, f"failed to upload recording for {response_json['upload_url']}"
                request = TranscriptionCreateRequest(recording_id=response_json["id"], template_name="General")
                response = await ac.post("/transcriptions", json=request.model_dump(mode="json"))
                assert response.status_code == 201, f"failed to create transcription for {request.model_dump_json()}"

                test_ids.add(response.json()["id"])
    return test_ids


def start_consumer(queue_service) -> asyncio.Task:
    consumer = Consumer(queue=queue_service, signal_handler=SignalHandler())
    return asyncio.create_task(consumer.run())


async def stop_consumer(task: asyncio.Task) -> None:
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


@requires_audio_data
@pytest.mark.asyncio(loop_scope="session")
async def test_e2e(worker_queue):
    consumer_task = start_consumer(worker_queue)
    try:
        transcription_ids = await load_db_test_instance(FileTypeTests.NORMAL)

        for transcription_id in transcription_ids:
            await assert_transcription_succeeds(transcription_id=transcription_id, consumer_task=consumer_task)
            await create_template_minutes(transcription_id)
            await assert_minute_templates_succeeds(transcription_id=transcription_id, consumer_task=consumer_task)

            await create_versions_for_ai_edit(transcription_id=transcription_id)
            await assert_minute_edit_succeeds(transcription_id=transcription_id, consumer_task=consumer_task)
    finally:
        await stop_consumer(consumer_task)


@requires_audio_data
@pytest.mark.asyncio(loop_scope="session")
async def test_e2e_zero_bytes(worker_queue):
    consumer_task = start_consumer(worker_queue)
    try:
        transcription_ids = await load_db_test_instance(FileTypeTests.ZERO_BYTES)
        for transcription_id in transcription_ids:
            await assert_transcription(
                transcription_id, consumer_task, loop_while_not=JobStatus.FAILED, fail_if=JobStatus.COMPLETED
            )
    finally:
        await stop_consumer(consumer_task)


@requires_audio_data
@pytest.mark.asyncio(loop_scope="session")
async def test_e2e_corrupted(worker_queue):
    consumer_task = start_consumer(worker_queue)
    try:
        transcription_ids = await load_db_test_instance(FileTypeTests.CORRUPTED)

        for transcription_id in transcription_ids:
            await assert_transcription(
                transcription_id, consumer_task, loop_while_not=JobStatus.FAILED, fail_if=JobStatus.COMPLETED
            )
    finally:
        await stop_consumer(consumer_task)


async def create_versions_for_ai_edit(transcription_id: UUID):
    async with get_test_client() as test_client:
        minutes = await get_minutes(transcription_id)
        for minute in minutes:
            for minute_version in minute.minute_versions:
                request = MinuteVersionCreateRequest(
                    content_source=ContentSource.AI_EDIT,
                    ai_edit_instructions=AiEdit(
                        instruction="Add a short haiku about the civil service at the end",
                        source_id=minute_version.id,
                    ),
                )
                response = await test_client.post(
                    f"/minutes/{minute_version.minute.id}/versions", json=request.model_dump(mode="json")
                )
                assert response.status_code == 200


async def check_worker(consumer_task: asyncio.Task):
    """If the consumer stops running, it's probably thrown an exception. Fail the test."""
    await asyncio.sleep(1)
    if consumer_task.done():
        pytest.fail(str(consumer_task.exception()))


async def assert_minute_edit_succeeds(transcription_id: UUID, consumer_task: asyncio.Task) -> None:
    completed = set()
    minutes = await get_minutes(transcription_id)
    assert len(minutes) == len(TEMPLATES), "Unexpected number of minutes"
    while len(completed) != len(minutes):
        print(f"AI Edit completed count: {len(completed)}, total required: {len(minutes)}")  # noqa: T201
        for minute in await get_minutes(transcription_id):
            if minute.id in completed:
                continue
            assert len(minute.minute_versions) == 2, f"There are {len(minute.minute_versions)}!"
            new, old = minute.minute_versions
            if new.status == JobStatus.COMPLETED:
                completed.add(minute.id)
                assert new.html_content != old.html_content, f"version {new.id} not changed by edit"
            elif new.status == JobStatus.FAILED:
                pytest.fail(f"Edit version {new.id} failed with error {new.error}")
        await asyncio.sleep(1)

        await check_worker(consumer_task)


async def assert_minute_templates_succeeds(transcription_id: UUID, consumer_task: asyncio.Task) -> None:
    minutes = await get_minutes(transcription_id)
    assert len(minutes) == len(TEMPLATES)
    completed_version_ids = set()
    while len(completed_version_ids) != len(TEMPLATES):
        print(  # noqa: T201
            f"""initial template completed count: {len(completed_version_ids)},
total required: {len(TEMPLATES)}"""
        )
        for minute in minutes:
            minute_versions = await get_minute_versions(minute.id)
            for minute_version in minute_versions:
                if minute_version.id in completed_version_ids:
                    continue
                match minute_version.status:
                    case JobStatus.COMPLETED:
                        completed_version_ids.add(minute.id)
                    case JobStatus.FAILED:
                        pytest.fail(f"Minute version {minute_version.id} failed: {minute_version.error}")
                    case _:
                        pass  # still pending; the outer loop polls until it completes or fails
            await asyncio.sleep(1)
        await check_worker(consumer_task)


async def create_template_minutes(transcription_id: UUID) -> None:
    async with get_test_client() as test_client:
        for template in TEMPLATES.values():
            # the General template is created by default after the initial transcription
            if template.name != "General":
                agenda = (
                    "Apologies for absence\nMain meeting discussion\nAny other business"
                    if template.agenda_usage is not AgendaUsage.NOT_USED
                    else None
                )
                request = MinutesCreateRequest(template_name=template.name, agenda=agenda)
                response = await test_client.post(
                    f"/transcription/{transcription_id}/minutes", json=request.model_dump(mode="json")
                )
                assert response.status_code == 200


async def assert_transcription_succeeds(transcription_id: UUID, consumer_task: asyncio.Task) -> None:
    transcription = await get_transcription(transcription_id)
    while transcription.status is not JobStatus.COMPLETED:
        transcription = await get_transcription(transcription_id)
        assert transcription.status is not JobStatus.FAILED
        # need to sleep here in order for the consumer to process during the test
        await asyncio.sleep(1)
        await check_worker(consumer_task)


async def get_transcription(transcription_id: UUID) -> Transcription:
    async with get_test_client() as test_client:
        transcription_response = await test_client.get(f"/transcriptions/{transcription_id}")
        assert (
            transcription_response.status_code == 200
        ), f"failed to get transcription, {transcription_response.json()}"
        return Transcription.model_validate(transcription_response.json())


async def get_minutes(transcription_id: UUID) -> list[Minute]:
    async with get_test_client() as test_client:
        response = await test_client.get(f"/transcription/{transcription_id}/minutes")
        assert response.status_code == 200
        minutes_without_versions = [Minute.model_validate(x) for x in response.json()]
        for minutes_without_version in minutes_without_versions:
            response = await test_client.get(f"/minutes/{minutes_without_version.id}/versions")
            assert response.status_code == 200
            minutes_without_version.minute_versions = [MinuteVersion.model_validate(x) for x in response.json()]
        return minutes_without_versions


async def get_minute_versions(minute_id: UUID) -> list[MinuteVersion]:
    async with get_test_client() as test_client:
        response = await test_client.get(f"/minutes/{minute_id}/versions")
        assert response.status_code == 200
        minutes_response_json = response.json()
        return [MinuteVersion.model_validate(x) for x in minutes_response_json]


async def assert_transcription(
    transcription_id: UUID,
    consumer_task: asyncio.Task,
    loop_while_not: JobStatus,
    fail_if: JobStatus,
) -> None:
    transcription = await get_transcription(transcription_id)

    while transcription.status is not loop_while_not:
        transcription = await get_transcription(transcription_id)
        assert transcription.status is not fail_if
        # need to sleep here in order for the consumer to process during the test
        await asyncio.sleep(1)
        await check_worker(consumer_task)


async def _create_recording_and_transcription() -> UUID:
    async with get_test_client() as test_client:
        response = await test_client.post(
            "/recordings", json=RecordingCreateRequest(file_extension="mp3").model_dump(mode="json")
        )
        assert response.status_code == 200
        recording = response.json()
        upload = requests.put(recording["upload_url"], data=b"not really audio", timeout=60)  # noqa: ASYNC210
        assert upload.status_code == 200
        response = await test_client.post(
            "/transcriptions",
            json=TranscriptionCreateRequest(recording_id=recording["id"], template_name="General").model_dump(
                mode="json"
            ),
        )
        assert response.status_code == 201
        return response.json()["id"]


@pytest.mark.asyncio(loop_scope="session")
async def test_e2e_failed_transcription_recovers_on_retry(worker_queue, monkeypatch):
    """Recovery: a transcription that fails is marked FAILED, and a user retry re-runs the
    pipeline to completion — STT/LLM stubbed, so this is offline and deterministic.

    This is the end-to-end version of the claim/lease recovery: the failed message is
    acked (never requeued), the user retry resets and republishes, and the worker
    re-processes from scratch.
    """
    attempts = {"n": 0}

    class FlakySTT:
        async def transcribe(self, _path):
            attempts["n"] += 1
            if attempts["n"] == 1:
                msg = "transient STT failure"
                raise RuntimeError(msg)
            return [{"speaker": "1", "text": "hello", "start_time": 0.0, "end_time": 1.0}]

    async def fake_prepare(_transcription, work_dir):
        return SimpleNamespace(file_path=work_dir / "audio.mp3")

    async def passthrough(entries):
        return entries

    async def fake_title(_entries):
        return "Recovered meeting"

    async def fake_compose(_minute):
        return "<p>ok</p>"

    monkeypatch.setattr(workflow, "transcription_service", FlakySTT())
    monkeypatch.setattr(workflow, "prepare_audio", fake_prepare)
    monkeypatch.setattr(workflow, "identify_speakers", passthrough)
    monkeypatch.setattr(workflow, "generate_meeting_title", fake_title)
    monkeypatch.setattr(workflow, "compose_minutes", fake_compose)
    monkeypatch.setattr(workflow, "capture_event", lambda *_args, **_kwargs: None)

    transcription_id = await _create_recording_and_transcription()
    consumer_task = start_consumer(worker_queue)
    try:
        await assert_transcription(
            transcription_id,
            consumer_task,
            loop_while_not=JobStatus.FAILED,
            fail_if=JobStatus.COMPLETED,
        )
        assert attempts["n"] == 1, "transcription should have failed exactly once"

        async with get_test_client() as test_client:
            response = await test_client.post(
                f"/transcriptions/{transcription_id}/retry", json={"template_name": "General"}
            )
        assert response.status_code == 201, response.json()

        await assert_transcription_succeeds(transcription_id, consumer_task)
        assert attempts["n"] == 2, "retry should re-run STT exactly once more"
    finally:
        await stop_consumer(consumer_task)
