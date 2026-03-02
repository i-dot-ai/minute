from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import soundfile as sf

from evals.transcription.src.adapters.azure import azure_st_adapter
from evals.transcription.src.adapters.whisply import whisply_adapter
from evals.transcription.src.evaluate import run_evaluation
from tests.evals.transcription.conftest import FakeAdapter, FakeDataset


@pytest.fixture
def setup_evaluation(tmp_path, monkeypatch):
    def _setup(samples_data, audio_duration=1.0, azure_hyp="hello world", whisper_hyp="good morning"):
        wav_files = []
        for i in range(len(samples_data)):
            wav_file = tmp_path / f"{chr(97 + i)}.wav"
            sf.write(wav_file, [0.0, 0.0], 16000, subtype="PCM_16")
            wav_files.append(wav_file)

        samples = [{"text": data["text"], "audio": {"path": str(wav_files[i])}} for i, data in enumerate(samples_data)]
        dataset = FakeDataset(samples)

        fake_settings = SimpleNamespace(AZURE_SPEECH_KEY="key", AZURE_SPEECH_REGION="region")
        monkeypatch.setattr("evals.transcription.src.evaluate.settings", fake_settings)
        monkeypatch.setattr("evals.transcription.src.evaluate.load_benchmark_dataset", lambda **_: dataset)
        monkeypatch.setattr("evals.transcription.src.evaluate.get_duration", lambda _: audio_duration)
        monkeypatch.setattr("evals.transcription.src.evaluate.WORKDIR", Path(tmp_path))

        monkeypatch.setattr(
            "evals.transcription.src.evaluate.azure_st_adapter",
            lambda **_: FakeAdapter("Azure Speech-to-Text", azure_hyp),
        )
        monkeypatch.setattr(
            "evals.transcription.src.evaluate.whisply_adapter",
            lambda **_: FakeAdapter("Whisper", whisper_hyp),
        )

        return tmp_path

    return _setup


def test_run_evaluation_with_fake_adapters(setup_evaluation):
    tmp_path = setup_evaluation(
        samples_data=[{"text": "hello world"}, {"text": "good morning"}],
        audio_duration=1.0,
        azure_hyp="hello world",
        whisper_hyp="good morning",
    )

    run_evaluation(num_samples=2)

    results_path = next((Path(tmp_path) / "results").glob("evaluation_results_*.json"))
    assert results_path.exists()
    results = json.loads(results_path.read_text(encoding="utf-8"))

    expected_structure = {
        "summaries": {
            "count": 2,
            "engines": {"Azure Speech-to-Text", "Whisper"},
            "required_fields": ["n_examples", "engine_version", "metrics"],
            "metrics_fields": ["wer"],
        },
        "samples": {
            "count_per_engine": 2,
            "required_fields": [
                "example_id",
                "engine_version",
                "reference_transcript",
                "hypothesis_transcript",
                "latency_recording_ratio",
                "metrics",
                "reference_dialogue_entries",
                "hypothesis_dialogue_entries",
            ],
            "metrics_fields": ["wer", "hits", "substitutions", "deletions", "insertions"],
        },
    }

    assert len(results["summaries"]) == expected_structure["summaries"]["count"]
    assert {s["engine_version"] for s in results["summaries"]} == expected_structure["summaries"]["engines"]

    for summary in results["summaries"]:
        assert summary["n_examples"] == 2
        assert all(field in summary for field in expected_structure["summaries"]["required_fields"])
        assert all(metric in summary["metrics"] for metric in expected_structure["summaries"]["metrics_fields"])

        engine = summary["engine_version"]
        samples = results["engines"][engine]
        assert len(samples) == expected_structure["samples"]["count_per_engine"]

        for idx, sample in enumerate(samples):
            assert sample["example_id"] == str(idx)
            assert sample["engine_version"] == engine
            assert all(field in sample for field in expected_structure["samples"]["required_fields"])
            assert all(metric in sample["metrics"] for metric in expected_structure["samples"]["metrics_fields"])


def test_processing_speed_ratio_calculation(setup_evaluation):
    tmp_path = setup_evaluation(
        samples_data=[{"text": "hello world"}],
        audio_duration=10.0,
        azure_hyp="hello world",
        whisper_hyp="hello world",
    )

    run_evaluation(num_samples=1)

    results_path = next((Path(tmp_path) / "results").glob("evaluation_results_*.json"))
    results = json.loads(results_path.read_text(encoding="utf-8"))

    for engine_samples in results["engines"].values():
        for sample in engine_samples:
            assert sample["latency_recording_ratio"] == pytest.approx(0.025)


@pytest.mark.parametrize(
    ("adapter_class", "monkeypatch_target"),
    [
        (azure_st_adapter, "evals.transcription.src.adapters.azure.CommonAzureAdapter.start"),
        (whisply_adapter, "common.services.transcription_services.whisply_local.WhisplyLocalAdapter.start"),
    ],
)
def test_adapter_contracts(tmp_path, monkeypatch, adapter_class, monkeypatch_target):
    async def fake_start(_path):
        return SimpleNamespace(
            transcript=[
                {"speaker": "Speaker 1", "text": "hello", "start_time": 0.0, "end_time": 0.5},
                {"speaker": "Speaker 1", "text": "world", "start_time": 0.5, "end_time": 1.0},
            ]
        )

    monkeypatch.setattr(monkeypatch_target, fake_start)

    wav_file = tmp_path / "test.wav"
    sf.write(wav_file, [0.0, 0.0], 16000, subtype="PCM_16")

    adapter = adapter_class()
    result = adapter.transcribe(str(wav_file))
    assert result.text == "hello world"
    assert result.duration_sec >= 0
    assert result.debug_info == {}


def test_run_evaluation_requires_azure_credentials(monkeypatch, tmp_path):
    wav_a = tmp_path / "a.wav"
    sf.write(wav_a, [0.0, 0.0], 16000, subtype="PCM_16")

    samples = [{"text": "hello world", "audio": {"path": str(wav_a)}}]
    dataset = FakeDataset(samples)
    fake_settings = SimpleNamespace(AZURE_SPEECH_KEY=None, AZURE_SPEECH_REGION=None)

    monkeypatch.setattr("common.services.transcription_services.azure.settings", fake_settings)
    monkeypatch.setattr("evals.transcription.src.evaluate.load_benchmark_dataset", lambda **_: dataset)
    monkeypatch.setattr("evals.transcription.src.evaluate.get_duration", lambda _: 1.0)
    monkeypatch.setattr("evals.transcription.src.evaluate.WORKDIR", Path(tmp_path))
    monkeypatch.setattr(
        "evals.transcription.src.evaluate.whisply_adapter",
        lambda **_: FakeAdapter("Whisper", "hello world"),
    )

    with pytest.raises(ValueError, match="Diarization data is required but missing"):
        run_evaluation(num_samples=1)
