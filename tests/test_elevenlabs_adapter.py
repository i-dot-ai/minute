import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from elevenlabs.core import ApiError

from common.database.postgres_models import Recording
from common.services.exceptions import TranscriptionFailedError
from common.services.transcription_services.adapter import AdapterType
from common.services.transcription_services.elevenlabs import ElevenLabsSpeechAdapter, _is_retryable


class FakeWord:
    """Stand-in for SpeechToTextWordResponseModel, which only needs these attributes here."""

    def __init__(self, text, start=None, end=None, type="word", speaker_id=None):  # noqa: A002
        self.text = text
        self.start = start
        self.end = end
        self.type = type
        self.speaker_id = speaker_id


def word(text, start, end, speaker):
    return FakeWord(text, start=start, end=end, type="word", speaker_id=speaker)


def spacing():
    return FakeWord(" ", type="spacing")


class TestConvertToDialogueEntries:
    def test_groups_consecutive_words_by_speaker(self):
        words = [
            word("Hello", 0.0, 0.5, "speaker_0"),
            spacing(),
            word("there.", 0.5, 1.0, "speaker_0"),
            spacing(),
            word("Hi", 1.2, 1.5, "speaker_1"),
            spacing(),
            word("back.", 1.5, 2.0, "speaker_1"),
        ]

        entries = ElevenLabsSpeechAdapter.convert_to_dialogue_entries(words)

        assert entries == [
            {"speaker": "speaker_0", "text": "Hello there.", "start_time": 0.0, "end_time": 1.0},
            {"speaker": "speaker_1", "text": "Hi back.", "start_time": 1.2, "end_time": 2.0},
        ]

    def test_speaker_can_take_multiple_turns(self):
        words = [
            word("One", 0.0, 1.0, "speaker_0"),
            word("Two", 1.0, 2.0, "speaker_1"),
            word("Three", 2.0, 3.0, "speaker_0"),
        ]

        entries = ElevenLabsSpeechAdapter.convert_to_dialogue_entries(words)

        assert [(e["speaker"], e["text"]) for e in entries] == [
            ("speaker_0", "One"),
            ("speaker_1", "Two"),
            ("speaker_0", "Three"),
        ]

    def test_inserts_a_space_when_spacing_items_are_absent(self):
        words = [word("Hello", 0.0, 0.5, "speaker_0"), word("there", 0.5, 1.0, "speaker_0")]

        entries = ElevenLabsSpeechAdapter.convert_to_dialogue_entries(words)

        assert entries[0]["text"] == "Hello there"

    def test_falls_back_to_a_single_speaker_when_diarization_returns_none(self):
        words = [word("Hello", 0.0, 0.5, None), spacing(), word("there", 0.5, 1.0, None)]

        entries = ElevenLabsSpeechAdapter.convert_to_dialogue_entries(words)

        assert len(entries) == 1
        assert entries[0]["speaker"] == "speaker_0"
        assert entries[0]["text"] == "Hello there"

    def test_handles_missing_timestamps(self):
        words = [
            word("Hello", None, None, "speaker_0"),
            spacing(),
            word("there", 4.0, 5.0, "speaker_0"),
        ]

        entries = ElevenLabsSpeechAdapter.convert_to_dialogue_entries(words)

        assert entries[0]["start_time"] == 0.0
        assert entries[0]["end_time"] == 5.0

    def test_keeps_audio_events_attached_to_their_speaker(self):
        words = [
            word("Hello", 0.0, 0.5, "speaker_0"),
            spacing(),
            FakeWord("(laughter)", start=0.5, end=1.0, type="audio_event", speaker_id="speaker_0"),
        ]

        entries = ElevenLabsSpeechAdapter.convert_to_dialogue_entries(words)

        assert len(entries) == 1
        assert entries[0]["text"] == "Hello (laughter)"

    def test_drops_entries_that_are_only_whitespace(self):
        assert ElevenLabsSpeechAdapter.convert_to_dialogue_entries([spacing(), spacing()]) == []
        assert ElevenLabsSpeechAdapter.convert_to_dialogue_entries([]) == []


class TestIsAvailable:
    @pytest.mark.parametrize(
        "api_key,model,expected",  # noqa: PT006
        [
            ("a-key", "scribe_v2", True),
            (None, "scribe_v2", False),
            ("", "scribe_v2", False),
            ("a-key", "", False),
        ],
    )
    def test_requires_an_api_key_and_a_model(self, api_key, model, expected):
        with patch("common.services.transcription_services.elevenlabs.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = api_key
            mock_settings.ELEVENLABS_STT_MODEL = model

            assert ElevenLabsSpeechAdapter.is_available() is expected


class TestIsRetryable:
    @pytest.mark.parametrize(
        "status_code,expected",  # noqa: PT006
        [(429, True), (500, True), (503, True), (401, False), (400, False), (404, False), (None, True)],
    )
    def test_retries_rate_limits_and_server_faults_only(self, status_code, expected):
        assert _is_retryable(ApiError(status_code=status_code, body="boom")) is expected

    def test_does_not_retry_unrelated_exceptions(self):
        assert _is_retryable(ValueError("nope")) is False


class TestStart:
    @pytest.fixture
    def audio_file(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file:
            temp_file.write(b"not really audio")
            temp_file.flush()
            yield Path(temp_file.name)

    @staticmethod
    def _patched_client(response):
        client = AsyncMock()
        client.speech_to_text.convert = AsyncMock(return_value=response)
        return patch("common.services.transcription_services.elevenlabs.AsyncElevenLabs", return_value=client), client

    @pytest.mark.asyncio
    async def test_returns_a_synchronous_transcript(self, audio_file):
        response = FakeWord("unused")
        response.words = [word("Hello", 0.0, 0.5, "speaker_0")]
        patcher, client = self._patched_client(response)

        with patcher:
            result = await ElevenLabsSpeechAdapter.start(audio_file)

        assert result.transcription_service == ElevenLabsSpeechAdapter.name
        assert result.transcript == [{"speaker": "speaker_0", "text": "Hello", "start_time": 0.0, "end_time": 0.5}]
        # A synchronous adapter must return the transcript from start(), never a job to poll.
        assert result.job_name == "synchronous"

        call_kwargs = client.speech_to_text.convert.call_args.kwargs
        assert call_kwargs["diarize"] is True
        assert call_kwargs["language_code"] == "eng"
        assert call_kwargs["file"][0] == audio_file.name

    @pytest.mark.asyncio
    async def test_raises_when_no_words_are_returned(self, audio_file):
        response = FakeWord("unused")
        response.words = []
        patcher, _ = self._patched_client(response)

        with patcher, pytest.raises(TranscriptionFailedError, match="No transcription words found"):
            await ElevenLabsSpeechAdapter.start(audio_file)

    @pytest.mark.asyncio
    async def test_raises_when_words_yield_no_dialogue(self, audio_file):
        response = FakeWord("unused")
        response.words = [spacing()]
        patcher, _ = self._patched_client(response)

        with patcher, pytest.raises(TranscriptionFailedError, match="no usable dialogue entries"):
            await ElevenLabsSpeechAdapter.start(audio_file)

    @pytest.mark.asyncio
    async def test_rejects_a_recording_instead_of_a_local_file(self):
        recording = Recording(user_id=uuid4(), s3_file_key="recording.mp3")
        patcher, _ = self._patched_client(FakeWord("unused"))

        with patcher as client_class, pytest.raises(TypeError, match="needs a local audio file"):
            await ElevenLabsSpeechAdapter.start(recording)

        client_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_the_configured_base_url(self, audio_file):
        response = FakeWord("unused")
        response.words = [word("Hello", 0.0, 0.5, "speaker_0")]
        patcher, _ = self._patched_client(response)
        # Deliberately not the EU residency default, so a hardcoded URL in the adapter would fail this.
        global_api = "https://api.elevenlabs.io"

        with (
            patcher as client_class,
            patch("common.services.transcription_services.elevenlabs.settings.ELEVENLABS_BASE_URL", global_api),
        ):
            await ElevenLabsSpeechAdapter.start(audio_file)

        # A data residency key is rejected by every stack but its own, so the URL has to reach the client.
        assert client_class.call_args.kwargs["base_url"] == global_api


class TestAdapterContract:
    def test_is_registered_with_the_manager(self):
        from common.services.transcription_services.transcription_manager import _adapters

        assert _adapters[ElevenLabsSpeechAdapter.name] is ElevenLabsSpeechAdapter

    def test_is_synchronous(self):
        assert ElevenLabsSpeechAdapter.adapter_type == AdapterType.SYNCHRONOUS

    @pytest.mark.asyncio
    async def test_check_passes_data_straight_through(self):
        from common.types import TranscriptionJobMessageData

        data = TranscriptionJobMessageData(transcription_service=ElevenLabsSpeechAdapter.name)

        assert await ElevenLabsSpeechAdapter.check(data) is data
