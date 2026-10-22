"""prepare_audio idempotency (newest-recording reuse) and conversion tests.

The reuse test is the regression guard for the plan's idempotency rule: on resume,
recordings[0] is the previously converted mp3, so no conversion/upload/new row happens.
"""

import shutil
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from common.audio.prepare_audio import prepare_audio
from common.database.postgres_database import AsyncSessionLocal, async_engine
from common.database.postgres_models import Recording, Transcription, User
from common.services.stt import Azure, TranscriptionFailedError, azure

ffmpeg_missing = shutil.which("ffmpeg") is None
requires_ffmpeg = pytest.mark.skipif(ffmpeg_missing, reason="ffmpeg not installed")

# The Runtime the helper runs with: the fake storage under test plus a real sessionmaker.
session_factory = async_sessionmaker(async_engine, expire_on_commit=False)


def _synth(path: Path, *, channels: int) -> Path:
    subprocess.run(  # noqa: S603
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-ac", str(channels), str(path)],  # noqa: S607
        check=True,
        capture_output=True,
    )
    return path


class FakeStorage:
    """The S3 client factory and the client it yields, faking the aioboto3 methods used."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.uploads: list[str] = []

    @asynccontextmanager
    async def __call__(self):
        yield self

    async def download_file(self, _bucket: str, key: str, filename: str) -> None:
        Path(filename).write_bytes(self.files.get(key, b"\0" * 64))

    async def upload_file(self, filename: str, _bucket: str, key: str) -> None:
        self.uploads.append(key)
        self.files[key] = Path(filename).read_bytes()


@pytest.fixture
def fake_storage():
    return FakeStorage()


@requires_ffmpeg
@pytest.mark.asyncio
async def test_reuses_newest_mp3_recording_without_converting(fake_storage, tmp_path):
    mono_mp3 = _synth(tmp_path / "mono.mp3", channels=1)
    original = Recording(id=uuid4(), s3_file_key=f"{uuid4()}.mp3", user_id=uuid4())
    fake_storage.files[original.s3_file_key] = mono_mp3.read_bytes()

    transcription = Transcription(id=uuid4(), recordings=[original])  # [0] is the newest

    prepared = await prepare_audio(transcription, tmp_path, fake_storage, session_factory)

    assert prepared.recording is original
    assert fake_storage.uploads == []


@requires_ffmpeg
@pytest.mark.asyncio
async def test_converts_multichannel_upload_and_persists_new_recording(fake_storage, tmp_path):
    stereo_wav = _synth(tmp_path / "stereo.wav", channels=2)
    async with AsyncSessionLocal() as session:
        user = User(email=f"{uuid4()}@test.co.uk")
        transcription = Transcription(id=uuid4())
        session.add(user)
        session.add(transcription)
        await session.commit()
        user_id, transcription_id = user.id, transcription.id

    # a transient view of the persisted transcription: prepare_audio only reads .id and .recordings
    original = Recording(id=uuid4(), s3_file_key=f"{uuid4()}.wav", user_id=user_id, transcription_id=transcription_id)
    fake_storage.files[original.s3_file_key] = stereo_wav.read_bytes()
    transcription = Transcription(id=transcription_id, recordings=[original])

    try:
        await prepare_audio(transcription, tmp_path, fake_storage, session_factory)

        assert len(fake_storage.uploads) == 1
        assert fake_storage.uploads[0].endswith(".mp3")
        async with AsyncSessionLocal() as session:
            from sqlmodel import select

            inserted = (
                await session.exec(select(Recording).where(Recording.s3_file_key == fake_storage.uploads[0]))
            ).first()
            assert inserted is not None
            assert inserted.transcription_id == transcription_id
            await session.delete(inserted)
            await session.commit()
    finally:
        async with AsyncSessionLocal() as session:
            row = await session.get(Transcription, transcription_id)
            if row:
                await session.delete(row)
            user_row = await session.get(User, user_id)
            if user_row:
                await session.delete(user_row)
            await session.commit()


@pytest.mark.asyncio
async def test_transcribe_requires_a_configured_service(monkeypatch):
    monkeypatch.setattr(azure.settings, "AZURE_SPEECH_KEY", None)
    with pytest.raises(TranscriptionFailedError, match="No transcription service is configured"):
        await Azure().transcribe(Path("whatever.mp3"))
