from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import soundfile as sf

from evals.transcription.src.adapters.registry import ADAPTER_REGISTRY
from evals.transcription.src.evaluate import run_evaluation
from tests.evals.transcription.conftest import FakeDataset


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

        class FakeAzureAdapter:
            name = "Azure Speech-to-Text"

            @classmethod
            async def start(cls, _audio_file_path):
                return SimpleNamespace(transcript=[{"text": azure_hyp}])

        class FakeWhisperAdapter:
            name = "Whisper"

            @classmethod
            async def start(cls, _audio_file_path):
                return SimpleNamespace(transcript=[{"text": whisper_hyp}])

        fake_registry = {
            "azure": (FakeAzureAdapter, "Azure Speech-to-Text"),
            "whisply": (FakeWhisperAdapter, "Whisper"),
        }

        fake_settings = SimpleNamespace(AZURE_SPEECH_KEY="key", AZURE_SPEECH_REGION="region")
        monkeypatch.setattr("evals.transcription.src.evaluate.settings", fake_settings)
        monkeypatch.setattr("evals.transcription.src.evaluate.load_benchmark_dataset", lambda **_: dataset)
        monkeypatch.setattr("evals.transcription.src.evaluate.get_duration", lambda _: audio_duration)
        monkeypatch.setattr("evals.transcription.src.evaluate.WORKDIR", Path(tmp_path))
        monkeypatch.setattr("evals.transcription.src.evaluate.ADAPTER_REGISTRY", fake_registry)

        return tmp_path

    return _setup


def test_run_evaluation_with_fake_adapters(setup_evaluation):
    tmp_path = setup_evaluation(
        samples_data=[{"text": "hello world"}, {"text": "good morning"}],
        audio_duration=1.0,
        azure_hyp="hello world",
        whisper_hyp="good morning",
    )

    run_evaluation(num_samples=2, adapter_names=["azure", "whisply"])

    results_path = next((Path(tmp_path) / "results").glob("evaluation_results_*.json"))
    assert results_path.exists()
    results = json.loads(results_path.read_text(encoding="utf-8"))

    assert len(results["summaries"]) == 2
    assert {s["engine"] for s in results["summaries"]} == {"Azure Speech-to-Text", "Whisper"}

    for summary in results["summaries"]:
        assert summary["num_samples"] == 2
        assert summary["overall_wer_pct"] >= 0.0

    azure_samples = results["engines"]["Azure Speech-to-Text"]
    assert len(azure_samples) == 2
    assert azure_samples[0]["dataset_index"] == 0
    assert azure_samples[0]["engine"] == "Azure Speech-to-Text"
    assert azure_samples[0]["ref_raw"] == "hello world"
    assert azure_samples[0]["hyp_raw"] == "hello world"
    assert azure_samples[0]["audio_sec"] == 1.0
    assert azure_samples[0]["process_sec"] > 0
    assert azure_samples[0]["engine_debug"] == {}
    assert {"equal", "replace", "delete", "insert"}.issubset(azure_samples[0]["diff_ops"])

    assert azure_samples[1]["dataset_index"] == 1
    assert azure_samples[1]["ref_raw"] == "good morning"
    assert azure_samples[1]["hyp_raw"] == "hello world"

    whisper_samples = results["engines"]["Whisper"]
    assert len(whisper_samples) == 2
    assert whisper_samples[0]["dataset_index"] == 0
    assert whisper_samples[0]["engine"] == "Whisper"
    assert whisper_samples[0]["ref_raw"] == "hello world"
    assert whisper_samples[0]["hyp_raw"] == "good morning"
    assert whisper_samples[0]["audio_sec"] == 1.0
    assert whisper_samples[0]["process_sec"] > 0
    assert whisper_samples[0]["engine_debug"] == {}

    assert whisper_samples[1]["dataset_index"] == 1
    assert whisper_samples[1]["ref_raw"] == "good morning"
    assert whisper_samples[1]["hyp_raw"] == "good morning"


def test_processing_speed_ratio_calculation(setup_evaluation):
    tmp_path = setup_evaluation(
        samples_data=[{"text": "hello world"}],
        audio_duration=10.0,
        azure_hyp="hello world",
        whisper_hyp="hello world",
    )

    run_evaluation(num_samples=1, adapter_names=["azure", "whisply"])

    results_path = next((Path(tmp_path) / "results").glob("evaluation_results_*.json"))
    results = json.loads(results_path.read_text(encoding="utf-8"))

    for engine_samples in results["engines"].values():
        for sample in engine_samples:
            expected_ratio = sample["process_sec"] / sample["audio_sec"]
            assert sample["processing_speed_ratio"] == pytest.approx(expected_ratio)
            assert sample["audio_sec"] == 10.0


@pytest.mark.parametrize(
    ("adapter_name", "monkeypatch_target"),
    [
        ("azure", "common.services.transcription_services.azure.AzureSpeechAdapter.start"),
        ("whisply", "common.services.transcription_services.whisply_local.WhisplyLocalAdapter.start"),
    ],
)
def test_adapter_contracts(tmp_path, monkeypatch, adapter_name, monkeypatch_target):
    async def fake_start(_path):
        return SimpleNamespace(transcript=[{"text": "hello"}, {"text": "world"}])

    monkeypatch.setattr(monkeypatch_target, fake_start)

    wav_file = tmp_path / "test.wav"
    sf.write(wav_file, [0.0, 0.0], 16000, subtype="PCM_16")

    from evals.transcription.src.adapters.base import ServiceTranscriptionAdapter

    adapter_class, adapter_name_str = ADAPTER_REGISTRY[adapter_name]
    adapter = ServiceTranscriptionAdapter(adapter_class, adapter_name_str)
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

    run_evaluation(num_samples=1, adapter_names=["azure"])

    results_path = next((Path(tmp_path) / "results").glob("evaluation_results_*.json"))
    results = json.loads(results_path.read_text(encoding="utf-8"))

    azure_samples = results["engines"]["Azure Speech-to-Text"]
    assert len(azure_samples) == 1
    assert "Azure credentials not found" in azure_samples[0]["engine_debug"]["error"]
