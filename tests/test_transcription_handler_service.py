import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.services.exceptions import StaleTranscriptionRunError, TranscriptionAlreadyStartedError
from common.services.transcription_handler_service import TranscriptionHandlerService
from common.types import TranscriptionJobMessageData, TranscriptionReadyMessageData


def test_claim_transcription_updates_once() -> None:
    session = MagicMock()
    session.exec.return_value.rowcount = 1

    with patch(
        "common.services.transcription_handler_service.SessionLocal"
    ) as session_local:
        session_local.return_value.__enter__.return_value = session
        TranscriptionHandlerService.claim_transcription(uuid.uuid4(), uuid.uuid4())

    session.commit.assert_called_once_with()


def test_claim_transcription_rejects_duplicate() -> None:
    session = MagicMock()
    session.exec.return_value.rowcount = 0

    with patch("common.services.transcription_handler_service.SessionLocal") as session_local:
        session_local.return_value.__enter__.return_value = session
        with pytest.raises(TranscriptionAlreadyStartedError):
            TranscriptionHandlerService.claim_transcription(uuid.uuid4(), uuid.uuid4())

    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_duplicate_ready_message_is_not_marked_failed() -> None:
    transcription = MagicMock(id=uuid.uuid4(), user_id=uuid.uuid4())

    with (
        patch.object(TranscriptionHandlerService, "get_transcription_from_minute_id", return_value=transcription),
        patch.object(
            TranscriptionHandlerService,
            "claim_transcription",
            side_effect=TranscriptionAlreadyStartedError,
        ),
        patch.object(TranscriptionHandlerService, "update_transcription") as update_transcription,
        patch(
            "common.services.transcription_handler_service.transcription_manager.perform_transcription_steps",
            new=AsyncMock(),
        ) as perform_transcription,
        pytest.raises(TranscriptionAlreadyStartedError),
    ):
        await TranscriptionHandlerService.process_transcription(
            minute_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            message_data=TranscriptionReadyMessageData(duration_seconds=10),
        )

    update_transcription.assert_not_called()
    perform_transcription.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_provider_success_does_not_complete_newer_run() -> None:
    transcription = MagicMock(id=uuid.uuid4(), user_id=uuid.uuid4())
    job = TranscriptionJobMessageData(
        transcription_service="test",
        transcript=[{"speaker": "A", "text": "hello", "start_time": 0.0, "end_time": 1.0}],
    )

    with (
        patch.object(TranscriptionHandlerService, "get_transcription_from_minute_id", return_value=transcription),
        patch.object(TranscriptionHandlerService, "is_current_transcription", return_value=True),
        patch.object(TranscriptionHandlerService, "identify_speakers", new=AsyncMock(return_value=job.transcript)),
        patch.object(TranscriptionHandlerService, "update_transcription", return_value=False),
        patch(
            "common.services.transcription_handler_service.transcription_manager.check_transcription",
            new=AsyncMock(return_value=job),
        ),
        patch(
            "common.services.transcription_handler_service.generate_meeting_title",
            new=AsyncMock(return_value="Title"),
        ),
        patch("common.services.transcription_handler_service.capture_event") as capture,
        pytest.raises(StaleTranscriptionRunError),
    ):
        await TranscriptionHandlerService.process_transcription(
            minute_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            message_data=job,
        )

    capture.assert_not_called()


@pytest.mark.asyncio
async def test_stale_provider_failure_does_not_fail_newer_run() -> None:
    transcription = MagicMock(id=uuid.uuid4(), user_id=uuid.uuid4())

    with (
        patch.object(TranscriptionHandlerService, "get_transcription_from_minute_id", return_value=transcription),
        patch.object(TranscriptionHandlerService, "claim_transcription"),
        patch.object(TranscriptionHandlerService, "update_transcription", return_value=False),
        patch(
            "common.services.transcription_handler_service.transcription_manager.perform_transcription_steps",
            new=AsyncMock(side_effect=RuntimeError("provider failed")),
        ),
        patch("common.services.transcription_handler_service.capture_event") as capture,
        pytest.raises(StaleTranscriptionRunError),
    ):
        await TranscriptionHandlerService.process_transcription(
            minute_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            message_data=TranscriptionReadyMessageData(duration_seconds=10),
        )

    capture.assert_not_called()
