import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from common.services.exceptions import TranscriptionFailedError
from common.services.transcription_handler_service import TranscriptionHandlerService
from common.services.transcription_services import sibrwdx
from common.services.transcription_services.sibrwdx import SibrwdxAdapter

FULL_SEGMENTS = [
    {
        "start": 0.908,
        "end": 21.226,
        "text": (
            "Ble rei di, ble rei di, yr hen dderyn bach? Un a thifri ar y goeden, "
            "pa mor uchel yw y pren, wel, dacw fo uwchben."
        ),
        "speaker": "SPEAKER_00",
    },
    {
        "start": 23.673,
        "end": 48.428,
        "text": "O mi syrthi yr hen dderyn bach. Blere di blere di yr hen dderyn bach. I rywle i dorri fy nghalon.",
        "speaker": "SPEAKER_00",
    },
    {
        "start": 48.952,
        "end": 69.117,
        "text": "Am rei di ffwrdd yn syth plant drwg fynd torri'r nyth o drueni yr hen dderyn bach.",
        "speaker": "SPEAKER_00",
    },
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("segments", "expected_processed"),
    [
        (
            [{"start": 0.908, "end": 9.97, "text": "Ble rei di?", "speaker": "SPEAKER_00"}],
            [{"speaker": "Gwen", "text": "Ble rei di?", "start_time": 0.908, "end_time": 9.97}],
        ),
        (
            FULL_SEGMENTS,
            [
                {
                    "speaker": "Gwen",
                    "text": " ".join(segment["text"] for segment in FULL_SEGMENTS),
                    "start_time": 0.908,
                    "end_time": 69.117,
                }
            ],
        ),
        (
            [FULL_SEGMENTS[0], {**FULL_SEGMENTS[1], "speaker": "SPEAKER_01"}, FULL_SEGMENTS[2]],
            [
                {"speaker": "Gwen", "text": FULL_SEGMENTS[0]["text"], "start_time": 0.908, "end_time": 21.226},
                {"speaker": "Dafydd", "text": FULL_SEGMENTS[1]["text"], "start_time": 23.673, "end_time": 48.428},
                {"speaker": "Gwen", "text": FULL_SEGMENTS[2]["text"], "start_time": 48.952, "end_time": 69.117},
            ],
        ),
    ],
    ids=["short", "full-same-speaker", "speaker-switch"],
)
async def test_sibrwdx_uploads_id_and_file_and_returns_azure_transcript_shape(
    monkeypatch, tmp_path, segments, expected_processed
):
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"test audio")
    transcription_id = str(uuid4())
    real_client = httpx.AsyncClient

    async def respond(request):
        assert str(request.url) == sibrwdx.settings.SIBRWDX_URL
        assert request.method == "POST"
        body = await request.aread()
        assert b'name="transcription_id"' in body
        assert transcription_id.encode() in body
        assert b'name="file"; filename="audio.mp3"' in body
        assert b"test audio" in body
        return httpx.Response(
            200,
            json={
                "language": "cy",
                "model": "techiaith/whisper-large-ft-cy-en-ct2",
                "device": "cuda",
                "segments": segments,
            },
        )

    def client(**kwargs):
        assert kwargs["timeout"] == 960
        return real_client(transport=httpx.MockTransport(respond), **kwargs)

    monkeypatch.setattr(sibrwdx.httpx, "AsyncClient", client)
    result = await SibrwdxAdapter.start(audio_file, transcription_id=transcription_id, timeout_seconds=1200)
    assert await SibrwdxAdapter.check(result) is result
    assert result.model_dump() == {
        "transcription_service": "sibrwdx",
        "job_name": "synchronous",
        "transcript_key": None,
        "transcript": [
            {
                "speaker": segment["speaker"],
                "text": segment["text"],
                "start_time": segment["start"],
                "end_time": segment["end"],
            }
            for segment in segments
        ],
    }
    predict_speakers = AsyncMock(return_value={"Speaker 1": "Gwen", "Speaker 2": "Dafydd"})
    monkeypatch.setattr("common.audio.speakers.generate_speaker_predictions", predict_speakers)
    assert await TranscriptionHandlerService.identify_speakers(result.transcript) == expected_processed
    predict_speakers.assert_awaited_once_with(
        [
            {**entry, "speaker": "Speaker 1" if entry["speaker"] == "Gwen" else "Speaker 2"}
            for entry in expected_processed
        ]
    )


@pytest.mark.asyncio
async def test_sibrwdx_rejects_failed_empty_or_malformed_responses(monkeypatch, tmp_path):
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"test audio")
    with pytest.raises(TypeError, match="requires a local audio file"):
        await SibrwdxAdapter.start("not a Path", transcription_id=str(uuid4()))
    with pytest.raises(ValueError, match="requires a transcription_id"):
        await SibrwdxAdapter.start(audio_file)
    real_client = httpx.AsyncClient
    for status, payload, expected_error in (
        (503, {"detail": "unavailable"}, httpx.HTTPStatusError),
        (200, {"segments": []}, TranscriptionFailedError),
        (200, {"segments": [{"text": "missing timestamps"}]}, TranscriptionFailedError),
        (200, {"segments": [{"start": "invalid", "end": 1, "speaker": "A", "text": "hi"}]}, TranscriptionFailedError),
        (200, [], TranscriptionFailedError),
    ):
        response = httpx.Response(status, json=payload)
        monkeypatch.setattr(
            sibrwdx.httpx,
            "AsyncClient",
            lambda response=response, **kwargs: real_client(
                transport=httpx.MockTransport(lambda _request: response), **kwargs
            ),
        )
        with pytest.raises(expected_error):
            await SibrwdxAdapter.start(audio_file, transcription_id=str(uuid4()))


@pytest.mark.asyncio
async def test_sibrwdx_whole_request_obeys_activity_budget(monkeypatch, tmp_path):
    async def hang(*_args, **_kwargs):
        await asyncio.Event().wait()

    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"test audio")
    monkeypatch.setattr(sibrwdx.httpx.AsyncClient, "post", hang)
    with pytest.raises(TimeoutError):
        await SibrwdxAdapter.start(audio_file, transcription_id=str(uuid4()), timeout_seconds=0.01)
