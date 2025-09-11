import asyncio
from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
import ray
import requests

from backend.app.minutes.types import (
    AgendaUsage,
    AiEdit,
    ChatCreateRequest,
    ChatGetResponse,
    MinutesCreateRequest,
    MinuteVersionCreateRequest,
    RecordingCreateRequest,
    TranscriptionCreateRequest,
)
from backend.services.queue_service import WorkerService, create_worker_service
from backend.services.queue_services import get_queue_service
from backend.services.template_manager import TemplateManager
from common.database.postgres_models import ContentSource, JobStatus, Minute, MinuteVersion, Transcription
from common.settings import get_settings
from tests.marks import costs_money
from tests.utils import FileTypeTests, get_test_client

pytestmark = [costs_money]


@pytest.fixture
def worker_service() -> Generator[WorkerService, Any, None]:
    worker_service = create_worker_service()
    yield worker_service
    ray.shutdown()


@pytest.fixture(autouse=True)
async def queue_service():
    queue_service = get_queue_service(get_settings().QUEUE_SERVICE_NAME)
    queue_service.purge_messages()
    # needed to ensure sqs queue is purged (not sure if this long is needed for localstack)
    await asyncio.sleep(1)
    return queue_service


async def load_db_test_instance(file_type: FileTypeTests) -> set[UUID]:
    # Note, needs MP3 files at the specified location
    async with get_test_client() as ac:
        test_audio_dir = Path(".data").joinpath("test_audio").joinpath(file_type.value)
        test_ids = set()
        for test_file in test_audio_dir.iterdir():
            request = RecordingCreateRequest(file_extension="mp3")
            response = await ac.post("/recordings", content=request.model_dump_json())
            assert response.status_code == 200, f"failed to create recording for  {request.model_dump_json()}"
            response_json = response.json()
            with test_file.open("rb") as f:
                http_response = requests.put(response_json["upload_url"], data=f.read(), timeout=60)  # noqa: ASYNC210
                assert http_response.status_code == 200, f"failed to upload recording for {response_json['upload_url']}"
                request = TranscriptionCreateRequest(recording_id=response_json["id"], template="General")
                response = await ac.post("/transcriptions", content=request.model_dump_json())
                assert response.status_code == 201, f"failed to create transcription for {request.model_dump_json()}"

                test_ids.add(response.json()["id"])
    return test_ids


@pytest.mark.requires_audio_data
@pytest.mark.asyncio(loop_scope="session")
async def test_e2e(worker_service):
    worker_service_task = asyncio.create_task(worker_service.run())
    transcription_ids = await load_db_test_instance(FileTypeTests.NORMAL)

    for transcription_id in transcription_ids:
        await assert_transcription_succeeds(transcription_id=transcription_id, receive_task=worker_service_task)
        await create_template_minutes(transcription_id)
        await assert_minute_templates_succeeds(transcription_id=transcription_id, receive_task=worker_service_task)

        await create_versions_for_ai_edit(transcription_id=transcription_id)
        await assert_minute_edit_succeeds(transcription_id=transcription_id, receive_task=worker_service_task)
    worker_service_task.cancel()


@pytest.mark.requires_audio_data
@pytest.mark.asyncio(loop_scope="session")
async def test_e2e_chat(worker_service):
    worker_service_task = asyncio.create_task(worker_service.run())

    # needed to ensure sqs queue is purged (not sure if this long is needed for localstack)
    await asyncio.sleep(1)
    transcription_ids = await load_db_test_instance(FileTypeTests.NORMAL)
    for transcription_id in transcription_ids:
        await assert_transcription_succeeds(transcription_id=transcription_id, receive_task=worker_service_task)
        chat_create_response = await create_chat(transcription_id)
        await assert_chat_succeeds(
            transcription_id=transcription_id,
            chat_id=chat_create_response,
            loop_while_not=JobStatus.COMPLETED,
            fail_if=JobStatus.FAILED,
        )
    # cancel the queue receiver
    worker_service_task.cancel()


@pytest.mark.requires_audio_data
@pytest.mark.asyncio(loop_scope="session")
async def test_e2e_zero_bytes(worker_service):
    worker_service_task = asyncio.create_task(worker_service.run())
    transcription_ids = await load_db_test_instance(FileTypeTests.ZERO_BYTES)
    for transcription_id in transcription_ids:
        await assert_transcription(
            transcription_id, worker_service_task, loop_while_not=JobStatus.FAILED, fail_if=JobStatus.COMPLETED
        )
    worker_service_task.cancel()


@pytest.mark.requires_audio_data
@pytest.mark.asyncio(loop_scope="session")
async def test_e2e_corrupted(worker_service):
    worker_service_task = asyncio.create_task(worker_service.run())
    transcription_ids = await load_db_test_instance(FileTypeTests.CORRUPTED)

    for transcription_id in transcription_ids:
        await assert_transcription(
            transcription_id, worker_service_task, loop_while_not=JobStatus.FAILED, fail_if=JobStatus.COMPLETED
        )
    worker_service_task.cancel()


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
                    f"/minutes/{minute_version.minute.id}/versions", content=request.model_dump_json()
                )
                assert response.status_code == 200


async def check_worker(receive_task):
    """If the worker stops running, it's probably thrown an exception. Fail the test."""
    await asyncio.sleep(1)
    if receive_task.done():
        pytest.fail(receive_task.result())


async def assert_minute_edit_succeeds(transcription_id: UUID, receive_task: asyncio.Task) -> None:
    completed = set()
    minutes = await get_minutes(transcription_id)
    assert len(minutes) == len(TemplateManager.templates), "Unexpected number of minutes"
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

        await check_worker(receive_task)


async def assert_minute_templates_succeeds(transcription_id: UUID, receive_task: asyncio.Task) -> None:
    minutes = await get_minutes(transcription_id)
    assert len(minutes) == len(TemplateManager.templates)
    completed_version_ids = set()
    while len(completed_version_ids) != len(TemplateManager.templates):
        print(  # noqa: T201
            f"""initial template completed count: {len(completed_version_ids)},
total required: {len(TemplateManager.templates)}"""
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
            await asyncio.sleep(1)
        await check_worker(receive_task)


async def assert_chat_succeeds(
    transcription_id: UUID,
    chat_id: UUID,
    loop_while_not: JobStatus,
    fail_if: JobStatus,
) -> None:
    chat = await get_chat(transcription_id=transcription_id, chat_id=chat_id)

    while chat.status is not loop_while_not:
        chat = await get_chat(transcription_id=transcription_id, chat_id=chat_id)
        assert chat.status is not fail_if
        # need to sleep here in order for worker threads to execute during test
        await asyncio.sleep(1)


async def create_template_minutes(transcription_id: UUID) -> None:
    async with get_test_client() as test_client:
        for template in TemplateManager.templates.values():
            # the General template is created by default after the initial transcription
            if template.name != "General":
                agenda = (
                    "Apologies for absence\nMain meeting discussion\nAny other business"
                    if template.agenda_usage is not AgendaUsage.NOT_USED
                    else None
                )
                request = MinutesCreateRequest(template_name=template.name, agenda=agenda)
                response = await test_client.post(
                    f"/transcription/{transcription_id}/minutes", content=request.model_dump_json()
                )
                assert response.status_code == 200


async def create_chat(transcription_id: UUID) -> UUID:
    async with get_test_client() as test_client:
        request = ChatCreateRequest(user_content="What did the Heath Minister say?")
        response = await test_client.post(f"/transcriptions/{transcription_id}/chat", content=request.model_dump_json())
        assert response.status_code == 201
        return UUID(response.json()["id"])


async def assert_transcription_succeeds(transcription_id: UUID, receive_task: asyncio.Task) -> None:
    transcription = await get_transcription(transcription_id)
    while transcription.status is not JobStatus.COMPLETED:
        transcription = await get_transcription(transcription_id)
        assert transcription.status is not JobStatus.FAILED
        # need to sleep here in order for worker threads to execute during test
        await asyncio.sleep(1)
        await check_worker(receive_task)


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


async def get_chat(transcription_id: UUID, chat_id: UUID) -> ChatGetResponse:
    async with get_test_client() as test_client:
        chat_response = await test_client.get(f"/transcriptions/{transcription_id}/chat/{chat_id}")
        assert chat_response.status_code == 200
        return ChatGetResponse.model_validate(chat_response.json())


async def get_minute_versions(minute_id: UUID) -> list[MinuteVersion]:
    async with get_test_client() as test_client:
        response = await test_client.get(f"/minutes/{minute_id}/versions")
        assert response.status_code == 200
        minutes_response_json = response.json()
        return [MinuteVersion.model_validate(x) for x in minutes_response_json]


async def assert_transcription(
    transcription_id: UUID,
    receive_task: asyncio.Task,
    loop_while_not: JobStatus,
    fail_if: JobStatus,
) -> None:
    transcription = await get_transcription(transcription_id)

    while transcription.status is not loop_while_not:
        transcription = await get_transcription(transcription_id)
        assert transcription.status is not fail_if
        # need to sleep here in order for worker threads to execute during test
        await asyncio.sleep(1)
        await check_worker(receive_task)
