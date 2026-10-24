"""E2E: upload audio -> Temporal runs transcribe, speakers, title, summary as separate activities.

Also covers the minute workflows: generating a user-created minute, and applying an AI edit.
Hits the running docker compose stack over HTTP (not in-process), so the real
backend, temporal server and worker are exercised. Calls Azure STT and the LLM.

    docker compose up -d --build --wait
    ALLOW_TESTS_TO_ACCESS_PAID_APIS=1 uv run pytest tests/test_temporal_transcription_e2e.py -s

Env: BACKEND_URL (default http://localhost:8080), TEMPORAL_ADDRESS (from .env).
"""

import asyncio
import os
from pathlib import Path

import httpx
import pytest
from temporalio.client import Client, WorkflowExecutionStatus

from common.settings import get_settings
from common.workflows.minute_version import workflow_id as minute_version_workflow_id
from common.workflows.transcription import (
    COMPLETE_TRANSCRIPTION,
    GENERATE_TITLE,
    IDENTIFY_SPEAKERS,
    LLM_TASK_QUEUE,
    PREPARE_AUDIO,
    STT_TASK_QUEUE,
    SUMMARIZE,
    TASK_QUEUE,
    TRANSCRIBE,
    workflow_id,
)
from tests.marks import costs_money

AUDIO = Path("frontend/tests/fixtures/sample-meeting.mp3")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
TIMEOUT_SECONDS = 600


async def _wait_for_version(api: httpx.AsyncClient, minute_id: str, version_id: str | None = None) -> dict:
    """Poll until the (newest) version of the minute is terminal; returns it."""
    versions: list = []
    for _ in range(TIMEOUT_SECONDS // 5):
        versions = (await api.get(f"/minutes/{minute_id}/versions")).raise_for_status().json()
        match = next((v for v in versions if version_id is None or v["id"] == version_id), None)
        if match and match["status"] in ("completed", "failed"):
            return match
        await asyncio.sleep(5)
    msg = f"minute version did not finish: {versions}"
    raise AssertionError(msg)


@costs_money
@pytest.mark.asyncio
async def test_upload_creates_transcription_via_temporal():
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=60) as api:
        recording = (await api.post("/recordings", json={"file_extension": "mp3"})).raise_for_status().json()
        # Local storage returns a frontend-proxied mock-storage path; S3 returns an absolute presigned URL.
        upload_url = recording["upload_url"]
        if upload_url.startswith("/"):
            upload_url = BACKEND_URL + upload_url.removeprefix("/api/proxy")
        (await api.put(upload_url, content=AUDIO.read_bytes())).raise_for_status()

        created = await api.post(
            "/transcriptions",
            json={"recording_id": recording["id"], "template_name": "General", "title": "Temporal e2e"},
        )
        assert created.status_code == 201, created.text
        transcription_id = created.json()["id"]
        print(f"\ntranscription {transcription_id}: workflow {workflow_id(transcription_id)}")  # noqa: T201

        status, body = None, {}
        for _ in range(TIMEOUT_SECONDS // 5):
            body = (await api.get(f"/transcriptions/{transcription_id}")).raise_for_status().json()
            status = body["status"]
            if status in ("completed", "failed"):
                break
            await asyncio.sleep(5)

    assert status == "completed", f"transcription ended {status}: {body.get('error')}"
    assert body["dialogue_entries"], "no transcript saved"

    settings = get_settings()
    client = await Client.connect(settings.TEMPORAL_ADDRESS, namespace=settings.TEMPORAL_NAMESPACE)
    handle = client.get_workflow_handle(workflow_id(transcription_id))
    outcome = await asyncio.wait_for(handle.result(), timeout=TIMEOUT_SECONDS)
    print(f"workflow outcome: {outcome}")  # noqa: T201
    assert (await handle.describe()).status == WorkflowExecutionStatus.COMPLETED
    assert outcome == {IDENTIFY_SPEAKERS: "ok", GENERATE_TITLE: "ok", SUMMARIZE: "ok"}

    # Each step is its own activity in the workflow history (visible in the Temporal UI).
    history = await handle.fetch_history()
    ran = [
        (a.activity_type.name, a.task_queue.name)
        for e in history.events
        if e.HasField("activity_task_scheduled_event_attributes")
        for a in [e.activity_task_scheduled_event_attributes]
    ]
    assert ran == [
        (PREPARE_AUDIO, STT_TASK_QUEUE),
        (TRANSCRIBE, STT_TASK_QUEUE),
        (IDENTIFY_SPEAKERS, LLM_TASK_QUEUE),
        (COMPLETE_TRANSCRIPTION, TASK_QUEUE),
        (GENERATE_TITLE, LLM_TASK_QUEUE),
        (SUMMARIZE, LLM_TASK_QUEUE),
    ]

    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=60) as api:
        # The title is written by a post-completion step, so it is only guaranteed once the
        # workflow (handle.result above) has finished.
        body = (await api.get(f"/transcriptions/{transcription_id}")).raise_for_status().json()
        minutes = (await api.get(f"/transcription/{transcription_id}/minutes")).raise_for_status().json()
        versions = (await api.get(f"/minutes/{minutes[0]['id']}/versions")).raise_for_status().json()
    assert body["title"], "no title generated"
    assert versions[0]["status"] == "completed", versions[0].get("error")
    assert versions[0]["html_content"], "no summary generated"

    # User-created minute: its own Temporal workflow (MinuteGenerationWorkflow).
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=60) as api:
        created_minute = (
            (await api.post(f"/transcription/{transcription_id}/minutes", json={"template_name": "General"}))
            .raise_for_status()
            .json()
        )
        generated = await _wait_for_version(api, created_minute["id"])
        assert generated["status"] == "completed", generated.get("error")
        assert generated["html_content"], "no minute generated"

        # AI edit: MinuteEditWorkflow over the generated version.
        edited = (
            (
                await api.post(
                    f"/minutes/{created_minute['id']}/versions",
                    json={
                        "content_source": "ai_edit",
                        "ai_edit_instructions": {
                            "instruction": "Add a one-line summary at the top",
                            "source_id": generated["id"],
                        },
                    },
                )
            )
            .raise_for_status()
            .json()
        )
        edited_version = await _wait_for_version(api, created_minute["id"], edited["id"])
    assert edited_version["status"] == "completed", edited_version.get("error")
    assert edited_version["html_content"], "no edited minute"

    for version_id in (generated["id"], edited["id"]):
        version_handle = client.get_workflow_handle(minute_version_workflow_id(version_id))
        assert (await version_handle.describe()).status == WorkflowExecutionStatus.COMPLETED
