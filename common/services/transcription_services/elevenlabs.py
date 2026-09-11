import logging
from pathlib import Path

import sentry_sdk
from elevenlabs.client import AsyncElevenLabs
from elevenlabs.core import ApiError
from elevenlabs.types.speech_to_text_word_response_model import SpeechToTextWordResponseModel
from tenacity import retry_if_exception

from common.database.postgres_models import DialogueEntry, Recording
from common.http_status import SERVER_ERROR, TOO_MANY_REQUESTS
from common.services.exceptions import TranscriptionFailedError
from common.services.transcription_services.adapter import AdapterType, TranscriptionAdapter
from common.services.transcription_services.retry import transcription_retry
from common.settings import get_settings
from common.types import TranscriptionJobMessageData

settings = get_settings()
logger = logging.getLogger(__name__)

# ElevenLabs diarises into "speaker_0", "speaker_1", ... but the field is optional, so fall back to a
# single speaker rather than dropping words when diarization returns nothing.
UNKNOWN_SPEAKER = "speaker_0"
# Scribe reports language as ISO-639-1 or ISO-639-3. There is no regional variant, so transcripts come
# back with American spellings; TranscriptionServiceManager converts those to British afterwards.
LANGUAGE_CODE = "eng"


def _is_retryable(exception: BaseException) -> bool:
    """Retry rate limits and server-side faults, but not auth or validation errors."""
    return isinstance(exception, ApiError) and (
        exception.status_code is None
        or exception.status_code == TOO_MANY_REQUESTS
        or exception.status_code >= SERVER_ERROR
    )


class ElevenLabsSpeechAdapter(TranscriptionAdapter):
    """Adapter for the ElevenLabs Scribe speech-to-text service."""

    # ElevenLabs accepts files up to 3GB and 10 hours of audio in a single request. Because this adapter is
    # synchronous, the real ceiling is whatever ELEVENLABS_STT_TIMEOUT_SECONDS allows the request to finish
    # in - raise that setting alongside this if you route very long recordings here.
    max_audio_length = 36000
    name = "elevenlabs_stt"
    adapter_type = AdapterType.SYNCHRONOUS

    @classmethod
    def is_available(cls) -> bool:
        return bool(settings.ELEVENLABS_API_KEY and settings.ELEVENLABS_STT_MODEL)

    @classmethod
    async def check(cls, data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        return data

    @classmethod
    @transcription_retry(retry_if_exception(_is_retryable))
    async def start(cls, audio_file_path_or_recording: Path | Recording) -> TranscriptionJobMessageData:
        """Transcribe a local audio file with the ElevenLabs Scribe API."""
        client = AsyncElevenLabs(api_key=settings.ELEVENLABS_API_KEY, timeout=settings.ELEVENLABS_STT_TIMEOUT_SECONDS)

        with sentry_sdk.start_transaction(op="process", name="post_file_to_elevenlabs_transcribe") as transaction:
            transaction.set_data("file_size", audio_file_path_or_recording.stat().st_size)
            transaction.set_data("file_type", audio_file_path_or_recording.suffix.lower())

            # Hand the SDK an open handle so httpx streams the upload instead of buffering the whole file.
            with audio_file_path_or_recording.open("rb") as audio_file:
                response = await client.speech_to_text.convert(
                    file=(audio_file_path_or_recording.name, audio_file, "audio/mpeg"),
                    model_id=settings.ELEVENLABS_STT_MODEL,
                    language_code=LANGUAGE_CODE,
                    diarize=True,
                    # Meeting minutes have no use for "(laughter)" style annotations in the transcript.
                    tag_audio_events=False,
                )

        # convert() is typed as a union: the multi-channel variant has no "words" attribute. We never ask
        # for multi-channel, so treat a response without words as a failure rather than assuming the shape.
        words = getattr(response, "words", None)
        if not words:
            msg = "No transcription words found in ElevenLabs response"
            raise TranscriptionFailedError(msg)

        transcript = cls.convert_to_dialogue_entries(words)
        if not transcript:
            msg = "ElevenLabs returned no usable dialogue entries"
            raise TranscriptionFailedError(msg)

        logger.info(
            "ElevenLabs transcribed %s into %d entries across %d speakers",
            audio_file_path_or_recording.name,
            len(transcript),
            len({entry["speaker"] for entry in transcript}),
        )
        return TranscriptionJobMessageData(transcription_service=cls.name, transcript=transcript)

    @classmethod
    def convert_to_dialogue_entries(cls, words: list[SpeechToTextWordResponseModel]) -> list[DialogueEntry]:
        """Group Scribe's word-level output into one dialogue entry per speaker turn.

        Scribe emits an item per word, per run of whitespace ("spacing") and per audio event, each tagged
        with the diarised speaker. The rest of the pipeline expects utterances, so consecutive items from
        the same speaker are merged.
        """
        entries: list[DialogueEntry] = []
        current: DialogueEntry | None = None

        for word in words:
            if not word.text:
                continue
            if word.type == "spacing":
                # Spacing carries the whitespace between words and no speaker of its own, so it extends
                # the entry in progress rather than starting a new one.
                if current is not None:
                    current["text"] += word.text
                continue

            speaker = word.speaker_id or UNKNOWN_SPEAKER
            start = word.start if word.start is not None else (current["end_time"] if current else 0.0)
            end = word.end if word.end is not None else start

            if current is None or current["speaker"] != speaker:
                current = DialogueEntry(speaker=speaker, text=word.text, start_time=start, end_time=end)
                entries.append(current)
            else:
                # Defensive: keeps words apart if a response ever omits the spacing items.
                if current["text"] and not current["text"][-1].isspace() and not word.text[:1].isspace():
                    current["text"] += " "
                current["text"] += word.text
                current["end_time"] = max(current["end_time"], end)

        for entry in entries:
            entry["text"] = entry["text"].strip()

        return [entry for entry in entries if entry["text"]]
