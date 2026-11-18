import pytest

from common.services.transcription_handler_service import TranscriptionHandlerService


@pytest.mark.asyncio(loop_scope="session")
async def test_owner_email_is_available_after_session_closes(minute_version_setup):
    transcription = TranscriptionHandlerService.get_transcription_from_minute_id(minute_version_setup["minute_id"])

    assert transcription.user.email == "minute-recovery-test@example.com"
