import uuid
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError
from tenacity import wait_none

from audio_worker import repository


def _failed_session() -> MagicMock:
    session = MagicMock()
    active_session = session.__enter__.return_value
    active_session.exec.return_value.rowcount = 1
    active_session.commit.side_effect = OperationalError("commit", {}, Exception())
    return session


def test_add_recording_retries_database_errors() -> None:
    successful_session = MagicMock()

    with (
        patch.object(cast(Any, repository.add_recording).retry, "wait", wait_none()),
        patch.object(repository, "SessionLocal", side_effect=[_failed_session(), successful_session]) as session_local,
    ):
        repository.add_recording(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "recording.mp3")

    assert session_local.call_count == 2


def test_mark_transcription_failed_reraises_after_retries() -> None:
    transcription_id = uuid.uuid4()
    minute_id = uuid.uuid4()

    with (
        patch.object(cast(Any, repository.mark_transcription_failed).retry, "wait", wait_none()),
        patch.object(repository, "SessionLocal", side_effect=[_failed_session() for _ in range(4)]) as session_local,
        pytest.raises(OperationalError),
    ):
        repository.mark_transcription_failed(transcription_id, minute_id, uuid.uuid4(), "failed")

    assert session_local.call_count == 4


def test_mark_transcription_failed_ignores_stale_run() -> None:
    session = MagicMock()
    session.exec.return_value.rowcount = 0

    with patch.object(repository, "SessionLocal") as session_local:
        session_local.return_value.__enter__.return_value = session
        changed = repository.mark_transcription_failed(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "failed")

    assert changed is False
    session.commit.assert_not_called()


def test_mark_transcription_failed_updates_current_run() -> None:
    session = MagicMock()
    session.exec.side_effect = [MagicMock(rowcount=1), MagicMock()]

    with patch.object(repository, "SessionLocal") as session_local:
        session_local.return_value.__enter__.return_value = session
        changed = repository.mark_transcription_failed(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "failed")

    assert changed is True
    assert session.exec.call_count == 2
    session.commit.assert_called_once_with()
