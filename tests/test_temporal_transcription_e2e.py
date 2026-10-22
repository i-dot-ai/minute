"""E2E: upload audio -> Temporal runs transcribe, speakers, title, summary as separate activities.

Hits the running docker compose stack over HTTP (not in-process), so the real
backend, temporal server and temporal-worker are exercised. Calls Azure STT.

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


@costs_money
@pytest.mark.asyncio
async def test_upload_creates_transcription_via_temporal():
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=60) as api:
        recording = (await api.post("/recordings", json={"file_extension": "mp3"})).raise_for_status().json()
        # Presigned S3 PUT against MiniStack (browser-facing endpoint, i.e. localhost:4566), as the frontend does.
        (await api.put(recording["upload_url"], content=AUDIO.read_bytes())).raise_for_status()

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
    assert body["title"], "no title generated"

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
        (GENERATE_TITLE, LLM_TASK_QUEUE),
        (COMPLETE_TRANSCRIPTION, TASK_QUEUE),
        (SUMMARIZE, LLM_TASK_QUEUE),
    ]

    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=60) as api:
        minutes = (await api.get(f"/transcription/{transcription_id}/minutes")).raise_for_status().json()
        versions = (await api.get(f"/minutes/{minutes[0]['id']}/versions")).raise_for_status().json()
    assert versions[0]["status"] == "completed", versions[0].get("error")
    assert versions[0]["html_content"], "no summary generated"
