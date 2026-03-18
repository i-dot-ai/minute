from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pytest

from evals.transcription.src.core.ami.loader import (
    AMIDatasetLoader,
    _apply_cutoff,
    _build_sample,
)
from evals.transcription.src.models import MeetingSegment, RawAudioDict, RawDatasetRow


def test_apply_cutoff_returns_all_when_no_cutoff():
    utterances = [
        RawDatasetRow(
            meeting_id="test",
            audio_id="1",
            text="a",
            audio=RawAudioDict(array=np.array([0.0]), sampling_rate=16000),
            begin_time=0.0,
            end_time=1.0,
            microphone_id="mic1",
            speaker_id="spk1",
        ),
        RawDatasetRow(
            meeting_id="test",
            audio_id="2",
            text="b",
            audio=RawAudioDict(array=np.array([0.0]), sampling_rate=16000),
            begin_time=1.0,
            end_time=2.0,
            microphone_id="mic1",
            speaker_id="spk1",
        ),
    ]

    result = _apply_cutoff(utterances, None)

    assert len(result) == 2


def test_apply_cutoff_filters_by_duration():
    utterances = [
        RawDatasetRow(
            meeting_id="test",
            audio_id="1",
            text="a",
            audio=RawAudioDict(array=np.array([0.0]), sampling_rate=16000),
            begin_time=0.0,
            end_time=1.0,
            microphone_id="mic1",
            speaker_id="spk1",
        ),
        RawDatasetRow(
            meeting_id="test",
            audio_id="2",
            text="b",
            audio=RawAudioDict(array=np.array([0.0]), sampling_rate=16000),
            begin_time=1.0,
            end_time=3.0,
            microphone_id="mic1",
            speaker_id="spk1",
        ),
    ]

    result = _apply_cutoff(utterances, 2.0)

    assert len(result) == 1
    assert result[0].text == "a"


def test_build_sample_creates_dataset_sample(tmp_path):
    audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    segment = MeetingSegment(meeting_id="ES2008a", utterance_cutoff_time=None)
    wav_path = tmp_path / "test.wav"
    ref_diar = [{"speaker": "Speaker_1", "text": "hello", "start_time": 0.0, "end_time": 1.0}]

    sample = _build_sample(audio, "hello world", segment, 0, wav_path, 5, ref_diar)

    assert sample.text == "hello world"
    assert sample.meeting_id == "ES2008a"
    assert sample.dataset_index == 0
    assert sample.num_utterances == 5
    assert sample.reference_diarization == ref_diar
    assert sample.audio.path == str(wav_path)


def test_ami_dataset_loader_initialization(tmp_path):
    loader = AMIDatasetLoader(
        cache_dir=tmp_path,
        num_samples=5,
        sample_duration_fraction=0.5,
        split="test",
        config="ihm",
    )

    assert loader.num_samples == 5
    assert loader.sample_duration_fraction == 0.5
    assert loader.split == "test"
    assert loader.config == "ihm"
    assert (tmp_path / "raw").exists()
    assert (tmp_path / "processed").exists()


def test_ami_dataset_loader_properties(tmp_path):
    loader = AMIDatasetLoader(cache_dir=tmp_path, num_samples=3)

    assert loader.dataset_version == "AMI_v0"
    assert loader.dataset_split == "n3"
    assert len(loader) == 0


def test_ami_dataset_loader_dataset_split_with_fraction(tmp_path):
    loader = AMIDatasetLoader(cache_dir=tmp_path, num_samples=3, sample_duration_fraction=0.5)

    assert loader.dataset_split == "n3_f0.5"


def test_ami_dataset_loader_dataset_split_none_when_no_params(tmp_path):
    loader = AMIDatasetLoader(cache_dir=tmp_path, num_samples=None, sample_duration_fraction=None)

    assert loader.dataset_split is None


def test_ami_dataset_loader_getitem_raises_on_invalid_index(tmp_path):
    loader = AMIDatasetLoader(cache_dir=tmp_path, num_samples=5)

    with pytest.raises(IndexError, match="Sample index .* out of range"):
        loader[0]


def test_ami_dataset_loader_prepare_returns_empty_when_no_segments(tmp_path, monkeypatch):
    def fake_select_segments(_metadata, _num_samples, _fraction):
        return []

    monkeypatch.setattr("evals.transcription.src.core.ami.loader.select_segments", fake_select_segments)
    monkeypatch.setattr("evals.transcription.src.core.ami.loader.load_or_build_metadata", lambda *_args: Mock())

    loader = AMIDatasetLoader(cache_dir=tmp_path, num_samples=5)
    samples = loader.prepare()

    assert samples == []


def test_ami_dataset_loader_load_required_utterances_returns_empty_when_cached(tmp_path):
    segment = MeetingSegment(meeting_id="ES2008a", utterance_cutoff_time=None)
    cache_audio = tmp_path / "processed" / "ES2008a_000000.mp3"
    cache_transcript = tmp_path / "processed" / "ES2008a_000000.txt"
    cache_audio.parent.mkdir(parents=True, exist_ok=True)
    cache_audio.write_bytes(b"audio")
    cache_transcript.write_bytes(b"text")

    loader = AMIDatasetLoader(cache_dir=tmp_path, num_samples=1)
    utterances = loader._load_required_utterances([segment])  # noqa: SLF001

    assert len(utterances) == 0


def test_ami_dataset_loader_process_segment_loads_from_cache(tmp_path, monkeypatch):
    segment = MeetingSegment(meeting_id="ES2008a", utterance_cutoff_time=None)
    cache_audio = tmp_path / "processed" / "ES2008a_000000.mp3"
    cache_transcript = tmp_path / "processed" / "ES2008a_000000.txt"
    cache_diar = tmp_path / "processed" / "ES2008a_000000_ref_diarization.json"
    cache_audio.parent.mkdir(parents=True, exist_ok=True)

    import soundfile as sf

    audio_data = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    temp_wav = tmp_path / "temp.wav"
    sf.write(temp_wav, audio_data, 16000)

    def fake_convert(_input_path, output_path):
        output_path.write_bytes(temp_wav.read_bytes())

    monkeypatch.setattr("evals.transcription.src.core.ami.cache.convert_to_mp3", fake_convert)

    cache_audio.write_bytes(temp_wav.read_bytes())
    cache_transcript.write_text("hello world", encoding="utf-8")
    cache_diar.write_text('[{"speaker": "Speaker_1", "text": "hello", "start_time": 0.0, "end_time": 1.0}]')

    loader = AMIDatasetLoader(cache_dir=tmp_path, num_samples=1)
    sample = loader._process_segment(segment, 0, {})  # noqa: SLF001

    assert sample is not None
    assert sample.text == "hello world"
    assert sample.meeting_id == "ES2008a"


def test_ami_dataset_loader_process_segment_returns_none_when_no_utterances(tmp_path):
    segment = MeetingSegment(meeting_id="ES2008a", utterance_cutoff_time=None)

    loader = AMIDatasetLoader(cache_dir=tmp_path, num_samples=1)
    sample = loader._process_segment(segment, 0, {})  # noqa: SLF001

    assert sample is None


def test_ami_dataset_loader_build_from_utterances(tmp_path, monkeypatch):
    segment = MeetingSegment(meeting_id="ES2008a", utterance_cutoff_time=None)
    utterances = [
        RawDatasetRow(
            meeting_id="ES2008a",
            audio_id="1",
            text="hello",
            audio=RawAudioDict(array=np.array([0.1, 0.2], dtype=np.float32), sampling_rate=16000),
            begin_time=0.0,
            end_time=0.125,
            microphone_id="mic1",
            speaker_id="Speaker_1",
        ),
    ]

    def fake_convert(_input_path, output_path):
        output_path.write_bytes(b"fake mp3")

    monkeypatch.setattr("evals.transcription.src.core.ami.cache.convert_to_mp3", fake_convert)

    loader = AMIDatasetLoader(cache_dir=tmp_path, num_samples=1)
    paths = loader.processed_cache_dir / "ES2008a_000000.mp3"

    sample = loader._build_from_utterances(  # noqa: SLF001
        utterances, Mock(audio=paths, transcript=paths.with_suffix(".txt")), segment, 0
    )

    assert sample is not None
    assert sample.text == "hello"
    assert sample.meeting_id == "ES2008a"
    assert paths.exists()
