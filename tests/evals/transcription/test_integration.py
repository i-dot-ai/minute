from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import soundfile as sf

from evals.transcription.src.adapters.azure import azure_st_adapter
from evals.transcription.src.adapters.whisper import whisper_st_adapter
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
            "evals.transcription.src.evaluate.whisper_st_adapter",
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

    assert len(results["summaries"]) == 2
    assert {s["engine"] for s in results["summaries"]} == {"Azure Speech-to-Text", "Whisper"}

    for summary in results["summaries"]:
        assert summary["num_samples"] == 2
        assert summary["overall_wer_pct"] >= 0.0
        assert "aggregated_metrics" in summary
        assert "wer" in summary["aggregated_metrics"]

        engine = summary["engine"]
        samples = results["engines"][engine]
        assert len(samples) == 2

        for idx, sample in enumerate(samples):
            assert sample["dataset_index"] == idx
            assert sample["engine"] == engine
            assert "ref_raw" in sample
            assert "hyp_raw" in sample
            assert "audio_sec" in sample
            assert "process_sec" in sample
            assert "processing_speed_ratio" in sample
            assert "metrics" in sample
            assert "wer" in sample["metrics"]
            assert "hits" in sample["metrics"]
            assert "substitutions" in sample["metrics"]
            assert "deletions" in sample["metrics"]
            assert "insertions" in sample["metrics"]
            assert "ref_normalized_with_speakers" in sample
            assert "hyp_normalized_with_speakers" in sample


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
            assert sample["processing_speed_ratio"] == pytest.approx(0.025)


@pytest.mark.parametrize(
    ("adapter_class", "monkeypatch_target"),
    [
        (azure_st_adapter, "evals.transcription.src.adapters.azure.CommonAzureAdapter.start"),
        (whisper_st_adapter, "evals.transcription.src.adapters.whisper.WhisplyLocalAdapter.start"),
    ],
)
def test_adapter_contracts(tmp_path, monkeypatch, adapter_class, monkeypatch_target):
    async def fake_start(_path):
        return SimpleNamespace(transcript=[{"text": "hello"}, {"text": "world"}])

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
        "evals.transcription.src.evaluate.whisper_st_adapter",
        lambda **_: FakeAdapter("Whisper", "hello world"),
    )

    run_evaluation(num_samples=1)

    results_path = next((Path(tmp_path) / "results").glob("evaluation_results_*.json"))
    results = json.loads(results_path.read_text(encoding="utf-8"))

    azure_samples = results["engines"]["Azure Speech API"]
    assert len(azure_samples) == 1
    assert "metrics" in azure_samples[0]
