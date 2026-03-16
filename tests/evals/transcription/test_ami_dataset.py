from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pytest

from evals.transcription.src.core.ami_dataset import _validate_dataset_contract, load_ami_dataset
from evals.transcription.src.models import AMIDatasetSample, AudioSample


def test_load_ami_dataset_with_num_samples(tmp_path, monkeypatch):
    mock_loader = Mock()
    mock_sample = Mock()
    mock_sample.audio = Mock(array=np.array([0.0]), sampling_rate=16000)
    mock_sample.text = "test"
    mock_loader.prepare.return_value = [mock_sample]

    def fake_loader(_cache_dir, num_samples, sample_duration_fraction):
        assert num_samples == 3
        assert sample_duration_fraction is None
        return mock_loader

    monkeypatch.setattr("evals.transcription.src.core.ami_dataset.AMIDatasetLoader", fake_loader)

    dataset = load_ami_dataset(tmp_path, num_samples=3)

    assert dataset == mock_loader
    mock_loader.prepare.assert_called_once()


def test_load_ami_dataset_with_duration_fraction(tmp_path, monkeypatch):
    mock_loader = Mock()
    mock_sample = Mock()
    mock_sample.audio = Mock(array=np.array([0.0]), sampling_rate=16000)
    mock_sample.text = "test"
    mock_loader.prepare.return_value = [mock_sample]

    def fake_loader(_cache_dir, num_samples, sample_duration_fraction):
        assert num_samples is None
        assert sample_duration_fraction == 0.5
        return mock_loader

    monkeypatch.setattr("evals.transcription.src.core.ami_dataset.AMIDatasetLoader", fake_loader)

    dataset = load_ami_dataset(tmp_path, num_samples=None, sample_duration_fraction=0.5)

    assert dataset == mock_loader


def test_load_ami_dataset_with_empty_samples(tmp_path, monkeypatch):
    mock_loader = Mock()
    mock_loader.prepare.return_value = []

    def fake_loader(_cache_dir, _num_samples, _sample_duration_fraction):
        return mock_loader

    monkeypatch.setattr("evals.transcription.src.core.ami_dataset.AMIDatasetLoader", fake_loader)

    dataset = load_ami_dataset(tmp_path, num_samples=None)

    assert dataset == mock_loader


def test_validate_dataset_contract_passes_valid_sample():
    sample = AMIDatasetSample(
        audio=AudioSample(array=np.array([0.0]), sampling_rate=16000, path="test.wav"),
        text="hello world",
        meeting_id="ES2008a",
        dataset_index=0,
        duration_sec=1.0,
        num_utterances=1,
        reference_diarization=[],
    )

    _validate_dataset_contract(sample)


def test_validate_dataset_contract_raises_when_no_audio():
    sample = Mock(spec=[])

    with pytest.raises(ValueError, match="Dataset row must contain 'audio'"):
        _validate_dataset_contract(sample)


def test_validate_dataset_contract_raises_when_no_text():
    sample = Mock(spec=["audio"])
    sample.audio = Mock()

    with pytest.raises(ValueError, match="Dataset row must contain 'text'"):
        _validate_dataset_contract(sample)


def test_validate_dataset_contract_raises_when_audio_no_array():
    sample = Mock()
    sample.audio = Mock(spec=[])
    sample.text = "test"

    with pytest.raises(ValueError, match="audio must contain 'array'"):
        _validate_dataset_contract(sample)


def test_validate_dataset_contract_raises_when_audio_no_sampling_rate():
    sample = Mock()
    sample.audio = Mock()
    sample.audio.array = np.array([0.0])
    sample.text = "test"
    delattr(sample.audio, "sampling_rate")

    with pytest.raises(ValueError, match="audio must contain 'sampling_rate'"):
        _validate_dataset_contract(sample)


def test_validate_dataset_contract_raises_when_text_not_string():
    sample = Mock()
    sample.audio = Mock(array=np.array([0.0]), sampling_rate=16000)
    sample.text = 123

    with pytest.raises(TypeError, match="'text' must be a string transcript"):
        _validate_dataset_contract(sample)
