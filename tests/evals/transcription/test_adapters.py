from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from evals.transcription.src.adapters.base import ServiceTranscriptionAdapter


def test_service_transcription_adapter_name():
    mock_adapter = Mock()
    mock_adapter.name = "TestAdapter"

    adapter = ServiceTranscriptionAdapter(mock_adapter)

    assert adapter.name == "TestAdapter"


def test_service_transcription_adapter_transcribe_success(tmp_path):
    mock_adapter = Mock()
    mock_adapter.name = "TestAdapter"

    async def fake_start(_path):
        return SimpleNamespace(
            transcript=[
                {"text": "hello", "speaker": "Speaker 1", "start_time": 0.0, "end_time": 1.0},
                {"text": "world", "speaker": "Speaker 1", "start_time": 1.0, "end_time": 2.0},
            ]
        )

    mock_adapter.start = fake_start

    adapter = ServiceTranscriptionAdapter(mock_adapter)
    wav_file = tmp_path / "test.wav"
    wav_file.write_bytes(b"fake audio")

    result = adapter.transcribe(str(wav_file))

    assert result.text == "hello world"
    assert result.duration_sec > 0
    assert len(result.dialogue_entries) == 2
    assert result.debug_info == {}


def test_service_transcription_adapter_transcribe_empty_transcript(tmp_path):
    mock_adapter = Mock()
    mock_adapter.name = "TestAdapter"

    async def fake_start(_path):
        return SimpleNamespace(transcript=[])

    mock_adapter.start = fake_start

    adapter = ServiceTranscriptionAdapter(mock_adapter)
    wav_file = tmp_path / "test.wav"
    wav_file.write_bytes(b"fake audio")

    result = adapter.transcribe(str(wav_file))

    assert result.text == ""
    assert result.duration_sec > 0
    assert result.dialogue_entries == []
    assert "error" in result.debug_info


def test_service_transcription_adapter_transcribe_handles_error(tmp_path):
    mock_adapter = Mock()
    mock_adapter.name = "TestAdapter"

    async def fake_start(_path):
        msg = "Transcription failed"
        raise RuntimeError(msg)

    mock_adapter.start = fake_start

    adapter = ServiceTranscriptionAdapter(mock_adapter)
    wav_file = tmp_path / "test.wav"
    wav_file.write_bytes(b"fake audio")

    result = adapter.transcribe(str(wav_file))

    assert result.text == ""
    assert result.duration_sec > 0
    assert result.dialogue_entries == []
    assert "error" in result.debug_info
    assert "Transcription failed" in result.debug_info["error"]


def test_service_transcription_adapter_transcribe_handles_value_error(tmp_path):
    mock_adapter = Mock()
    mock_adapter.name = "TestAdapter"

    async def fake_start(_path):
        msg = "Invalid input"
        raise ValueError(msg)

    mock_adapter.start = fake_start

    adapter = ServiceTranscriptionAdapter(mock_adapter)
    wav_file = tmp_path / "test.wav"
    wav_file.write_bytes(b"fake audio")

    result = adapter.transcribe(str(wav_file))

    assert result.text == ""
    assert "Invalid input" in result.debug_info["error"]


def test_service_transcription_adapter_transcribe_handles_os_error(tmp_path):
    mock_adapter = Mock()
    mock_adapter.name = "TestAdapter"

    async def fake_start(_path):
        msg = "File not found"
        raise OSError(msg)

    mock_adapter.start = fake_start

    adapter = ServiceTranscriptionAdapter(mock_adapter)
    wav_file = tmp_path / "test.wav"
    wav_file.write_bytes(b"fake audio")

    result = adapter.transcribe(str(wav_file))

    assert result.text == ""
    assert "File not found" in result.debug_info["error"]
