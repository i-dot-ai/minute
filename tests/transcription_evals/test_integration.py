from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import soundfile as sf

from evals.transcription.src.adapters.azure import AzureSTTAdapter
from evals.transcription.src.adapters.whisply import WhisplyAdapter
from evals.transcription.src.evaluate import run_evaluation
from tests.transcription_evals.conftest import FakeAdapter, FakeDataset


def test_run_evaluation_with_fake_adapters(tmp_path, monkeypatch):
    wav_a = tmp_path / "a.wav"
    wav_b = tmp_path / "b.wav"
    sf.write(wav_a, [0.0, 0.0], 16000, subtype="PCM_16")
    sf.write(wav_b, [0.0, 0.0], 16000, subtype="PCM_16")

    samples = [
        {"text": "hello world", "audio": {"path": str(wav_a)}},
        {"text": "good morning", "audio": {"path": str(wav_b)}},
    ]
    dataset = FakeDataset(samples)

    fake_settings = SimpleNamespace(AZURE_SPEECH_KEY="key", AZURE_SPEECH_REGION="region")
    monkeypatch.setattr("evals.transcription.src.evaluate.settings", fake_settings)
    monkeypatch.setattr("evals.transcription.src.evaluate.load_benchmark_dataset", lambda **_: dataset)
    monkeypatch.setattr("evals.transcription.src.evaluate.get_duration", lambda _: 1.0)
    monkeypatch.setattr("evals.transcription.src.evaluate.WORKDIR", Path(tmp_path))

    monkeypatch.setattr(
        "evals.transcription.src.evaluate.AzureSTTAdapter",
        lambda **_: FakeAdapter("Azure Speech-to-Text", "hello world"),
    )
    monkeypatch.setattr(
        "evals.transcription.src.evaluate.WhisplyAdapter",
        lambda **_: FakeAdapter("Whisply", "good morning"),
    )

    run_evaluation(num_samples=2)

    results_path = next((Path(tmp_path) / "results").glob("evaluation_results_*.json"))
    assert results_path.exists()
    results_data = json.loads(results_path.read_text(encoding="utf-8"))

    assert "run_info" in results_data
    assert "summaries" in results_data
    assert "engines" in results_data

    run_info = results_data["run_info"]
    assert "dataset_version" in run_info
    assert run_info["total_audio_sec"] >= 0.0
    assert run_info["total_words"] >= 0

    summaries = results_data["summaries"]
    engines_samples = results_data["engines"]

    assert len(summaries) == 2
    assert {s["engine"] for s in summaries} == {"Azure Speech-to-Text", "Whisply"}

    for summary in summaries:
        engine_name = summary["engine"]
        assert summary["processing_speed_ratio"] >= 0.0
        assert summary["process_sec"] >= 0.0
        assert "aggregated_metrics" in summary
        assert "wer" in summary["aggregated_metrics"]
        assert "jaccard_wer" in summary["aggregated_metrics"]
        assert summary["speaker_count_accuracy"] >= 0.0
        assert summary["total_hits"] >= 0
        assert summary["total_substitutions"] >= 0
        assert summary["total_deletions"] >= 0
        assert summary["total_insertions"] >= 0

        samples_out = engines_samples[engine_name]
        assert [s["dataset_index"] for s in samples_out] == [0, 1]
        for sample in samples_out:
            assert sample["engine"] == engine_name
            assert sample["audio_sec"] == 1.0
            assert sample["process_sec"] == 0.25
            assert sample["processing_speed_ratio"] == 0.25
            assert sample["ref_raw"]
            assert sample["hyp_raw"]
            assert isinstance(sample["metrics"], dict)
            assert "wer" in sample["metrics"]
            assert "jaccard_wer" in sample["metrics"]
            assert isinstance(sample["metrics"]["wer"], float)
            assert "hits" in sample["metrics"]
            assert "substitutions" in sample["metrics"]
            assert "deletions" in sample["metrics"]
            assert "insertions" in sample["metrics"]
            assert "dialogue_entries" not in sample
            assert "reference_diarization" not in sample
            assert "ref_normalized_with_speakers" in sample
            assert "hyp_normalized_with_speakers" in sample


def test_adapter_contracts(tmp_path, monkeypatch):
    async def fake_start(_path):
        return SimpleNamespace(
            transcript=[
                {"text": "hello", "speaker": "Speaker_1", "start_time": 0.0, "end_time": 0.5},
                {"text": "world", "speaker": "Speaker_2", "start_time": 0.5, "end_time": 1.0},
            ]
        )

    monkeypatch.setattr("evals.transcription.src.adapters.azure.CommonAzureAdapter.start", fake_start)
    monkeypatch.setattr("evals.transcription.src.adapters.whisply.CommonWhisplyAdapter.start", fake_start)

    wav_a = tmp_path / "a.wav"
    wav_b = tmp_path / "b.wav"
    sf.write(wav_a, [0.0, 0.0], 16000, subtype="PCM_16")
    sf.write(wav_b, [0.0, 0.0], 16000, subtype="PCM_16")

    azure = AzureSTTAdapter()
    result = azure.transcribe(str(wav_a))
    assert isinstance(result["text"], str)
    assert isinstance(result["duration_sec"], float)
    assert isinstance(result["dialogue_entries"], list)
    assert isinstance(result["debug_info"], dict)
    assert len(result["dialogue_entries"]) == 2
    assert result["dialogue_entries"][0]["speaker"] == "Speaker_1"
    assert result["dialogue_entries"][0]["text"] == "hello"
    assert result["dialogue_entries"][0]["start_time"] == 0.0
    assert result["dialogue_entries"][0]["end_time"] == 0.5
    assert result["dialogue_entries"][1]["speaker"] == "Speaker_2"
    assert result["dialogue_entries"][1]["text"] == "world"
    assert result["text"] == "hello world"
    assert result["duration_sec"] > 0

    whisply = WhisplyAdapter()
    result = whisply.transcribe(str(wav_b))
    assert isinstance(result["text"], str)
    assert isinstance(result["duration_sec"], float)
    assert isinstance(result["dialogue_entries"], list)
    assert isinstance(result["debug_info"], dict)
    assert len(result["dialogue_entries"]) == 2
    assert result["dialogue_entries"][0]["speaker"] == "Speaker_1"
    assert result["dialogue_entries"][1]["speaker"] == "Speaker_2"
    assert result["text"] == "hello world"
    assert result["duration_sec"] > 0


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
        "evals.transcription.src.evaluate.WhisplyAdapter",
        lambda **_: FakeAdapter("Whisply", "hello world"),
    )

    run_evaluation(num_samples=1)

    results_path = next((Path(tmp_path) / "results").glob("evaluation_results_*.json"))
    results = json.loads(results_path.read_text(encoding="utf-8"))

    assert "run_info" in results
    assert "summaries" in results
    assert "engines" in results
    assert "Azure Speech API" in results["engines"]
    assert "Whisply" in results["engines"]

    azure_samples = results["engines"]["Azure Speech API"]
    assert len(azure_samples) == 1
    azure_sample = azure_samples[0]
    assert azure_sample["engine"] == "Azure Speech API"
    assert azure_sample["dataset_index"] == 0
    assert azure_sample["hyp_raw"] == ""
    assert "ref_normalized_with_speakers" in azure_sample
    assert "hyp_normalized_with_speakers" in azure_sample
    assert azure_sample["audio_sec"] == 1.0
    assert azure_sample["process_sec"] > 0
    assert isinstance(azure_sample["metrics"], dict)
    assert "dialogue_entries" not in azure_sample

    whisply_samples = results["engines"]["Whisply"]
    assert len(whisply_samples) == 1
    whisply_sample = whisply_samples[0]
    assert whisply_sample["engine"] == "Whisply"
    assert whisply_sample["hyp_raw"] == "hello world"
    assert whisply_sample["audio_sec"] == 1.0
