import asyncio
from pathlib import Path

import httpx

from common.database.postgres_models import Recording
from common.services.exceptions import TranscriptionFailedError
from common.services.transcription_services.adapter import AdapterType, TranscriptionAdapter
from common.settings import get_settings
from common.types import TranscriptionJobMessageData

settings = get_settings()
TIMEOUT_SECONDS = 960


class SibrwdxAdapter(TranscriptionAdapter):
    name = "sibrwdx"
    adapter_type = AdapterType.SYNCHRONOUS
    # shortcut: Azure's 17999s audio limit is assumed for testing, confirm Sibrwdx's limit before production.
    max_audio_length = 17999

    @classmethod
    def is_available(cls) -> bool:
        return bool(settings.SIBRWDX_URL)

    @classmethod
    async def check(cls, data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        return data

    @classmethod
    async def start(
        cls,
        audio_file_path_or_recording: Path | Recording,
        timeout_seconds: float | None = None,
        attempt: int = 1,  # noqa: ARG003
        transcription_id: str | None = None,
    ) -> TranscriptionJobMessageData:
        if not isinstance(audio_file_path_or_recording, Path):
            msg = "Synchronous transcription requires a local audio file"
            raise TypeError(msg)
        if not transcription_id:
            msg = "Sibrwdx requires a transcription_id"
            raise ValueError(msg)
        timeout = min(timeout_seconds or TIMEOUT_SECONDS, TIMEOUT_SECONDS)
        with audio_file_path_or_recording.open("rb") as audio_file:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with asyncio.timeout(timeout):
                    response = await client.post(
                        settings.SIBRWDX_URL,
                        data={"transcription_id": transcription_id},
                        files={"file": (audio_file_path_or_recording.name, audio_file, "audio/mpeg")},
                    )
                response.raise_for_status()
        try:
            segments = response.json().get("segments")
            if not segments:
                msg = "No transcription phrases found in response"
                raise TranscriptionFailedError(msg)
            return TranscriptionJobMessageData(
                transcription_service=cls.name,
                transcript=[
                    {
                        "speaker": segment["speaker"],
                        "text": segment["text"],
                        "start_time": segment["start"],
                        "end_time": segment["end"],
                    }
                    for segment in segments
                ],
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            msg = "Invalid Sibrwdx transcription response"
            raise TranscriptionFailedError(msg) from exc
