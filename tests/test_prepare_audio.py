"""prepare_audio idempotency (newest-recording reuse) and conversion tests.

The reuse test is the regression guard for the plan's idempotency rule: on resume,
recordings[0] is the previously converted mp3, so no conversion/upload/new row happens.
"""

import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

from common.database.postgres_database import AsyncSessionLocal
from common.database.postgres_models import Recording, Transcription
from worker.actions import prepare_audio as prepare_audio_module
from worker.actions import transcribe as transcribe_module
from worker.actions.prepare_audio import prepare_audio
from worker.errors import TranscriptionFailedError

ffmpeg_missing = shutil.which("ffmpeg") is None
requires_ffmpeg = pytest.mark.skipif(ffmpeg_missing, reason="ffmpeg not installed")


def _synth(path: Path, *, channels: int) -> Path:
    subprocess.run(  # noqa: S603
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-ac", str(channels), str(path)],  # noqa: S607
        check=True,
        capture_output=True,
    )
    return path


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.uploads: list[str] = []

    async def download(self, key: str, path: Path) -> None:
        path.write_bytes(self.files.get(key, b"\0" * 64))

    async def upload(self, key: str, path: Path) -> None:
        self.uploads.append(key)
        self.files[key] = path.read_bytes()

    async def check_object_exists(self, key: str) -> bool:
        return key in self.files


@pytest.fixture
def fake_storage(monkeypatch):
    storage = FakeStorage()
    monkeypatch.setattr(prepare_audio_module, "storage_service", storage)
    return storage


@requires_ffmpeg
async def test_reuses_newest_mp3_recording_without_converting(fake_storage, tmp_path):
    mono_mp3 = _synth(tmp_path / "mono.mp3", channels=1)
    original = Recording(id=uuid4(), s3_file_key=f"{uuid4()}.mp3", user_id=uuid4())
    fake_storage.files[original.s3_file_key] = mono_mp3.read_bytes()

    transcription = Transcription(id=uuid4(), recordings=[original])  # [0] is the newest

    prepared = await prepare_audio(transcription, work_dir=tmp_path)

    assert prepared.recording is original
    assert fake_storage.uploads == []


@requires_ffmpeg
async def test_converts_multichannel_upload_and_persists_new_recording(fake_storage, tmp_path):
    stereo_wav = _synth(tmp_path / "stereo.wav", channels=2)
    async with AsyncSessionLocal() as session:
        transcription = Transcription(id=uuid4())
        session.add(transcription)
        await session.commit()
    original = Recording(id=uuid4(), s3_file_key=f"{uuid4()}.wav", user_id=uuid4(), transcription_id=transcription.id)
    fake_storage.files[original.s3_file_key] = stereo_wav.read_bytes()
    transcription.recordings = [original]

    try:
        await prepare_audio(transcription, work_dir=tmp_path)

        assert len(fake_storage.uploads) == 1
        assert fake_storage.uploads[0].endswith(".mp3")
        async with AsyncSessionLocal() as session:
            from sqlmodel import select

            inserted = (
                await session.exec(select(Recording).where(Recording.s3_file_key == fake_storage.uploads[0]))
            ).first()
            assert inserted is not None
            assert inserted.transcription_id == transcription.id
            await session.delete(inserted)
            await session.commit()
    finally:
        async with AsyncSessionLocal() as session:
            row = await session.get(Transcription, transcription.id)
            if row:
                await session.delete(row)
                await session.commit()


@pytest.mark.asyncio
async def test_transcribe_audio_requires_a_configured_service(monkeypatch):
    monkeypatch.setattr(transcribe_module.settings, "AZURE_SPEECH_KEY", None)
    with pytest.raises(TranscriptionFailedError, match="No transcription service is configured"):
        await transcribe_module.transcribe_audio(Path("whatever.mp3"))
