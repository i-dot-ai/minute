import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

from tqdm import tqdm

from evals.transcription.src.adapters.base import EvalsTranscriptionAdapter
from evals.transcription.src.core.metrics import (
    compute_speaker_count_metrics,
    compute_wder,
    compute_wer_metrics,
    normalise_text,
)
from evals.transcription.src.core.results import create_summary
from evals.transcription.src.core.segments import (
    convert_to_diarization_format,
    format_segments_with_speakers,
)
from evals.transcription.src.models import (
    DatasetProtocol,
    DiarizationSegment,
    DurationFn,
    EngineOutput,
    EngineResults,
    SampleMetrics,
    SampleRow,
    TimingAccumulator,
    WavWriteFn,
)

logger = logging.getLogger(__name__)


def _extract_segments(result: Any, example: Any) -> tuple[list, list]:
    dialogue_entries = result.dialogue_entries if hasattr(result, "dialogue_entries") else []
    reference_diarization = example.reference_diarization if hasattr(example, "reference_diarization") else []
    return dialogue_entries, reference_diarization


def _compute_base_wer_metrics(ref_raw: str, hyp_raw: str) -> SampleMetrics:
    reference_normalized = normalise_text(ref_raw)
    hypothesis_normalized = normalise_text(hyp_raw)
    wer_metrics = compute_wer_metrics([reference_normalized], [hypothesis_normalized])

    return SampleMetrics(
        wer=wer_metrics.wer,
        hits=wer_metrics.hits,
        substitutions=wer_metrics.substitutions,
        deletions=wer_metrics.deletions,
        insertions=wer_metrics.insertions,
    )


def _process_diarization(
    reference_diarization: list,
    dialogue_entries: list,
    metrics: SampleMetrics,
) -> tuple[list[DiarizationSegment], list[DiarizationSegment]]:
    ref_diar_dicts: list[DiarizationSegment] = []
    hyp_diar_dicts: list[DiarizationSegment] = []

    if reference_diarization and dialogue_entries:
        ref_diar_dicts = convert_to_diarization_format(reference_diarization)
        hyp_diar_dicts = convert_to_diarization_format(dialogue_entries)
        _compute_diarization_metrics(ref_diar_dicts, hyp_diar_dicts, metrics)

    return ref_diar_dicts, hyp_diar_dicts


def run_engines_parallel(
    adapters_config: Sequence[EvalsTranscriptionAdapter],
    indices: list[int],
    *,
    dataset: DatasetProtocol,
    wav_write_fn: WavWriteFn,
    duration_fn: DurationFn,
    max_workers: int | None = None,
) -> list[EngineOutput]:
    """
    Runs multiple transcription adapters in parallel on dataset samples and computes WER metrics.
    """
    total_tasks = len(indices) * len(adapters_config)
    progress_bar = tqdm(total=total_tasks, desc="Processing all engines", unit="task")
    progress_bar_lock = Lock()

    results: dict[str, EngineResults] = {}

    def process_sample(
        adapter: EvalsTranscriptionAdapter,
        index: int,
    ) -> tuple[str, int, SampleRow, float, float]:
        """
        Transcribes a single sample and computes WER metrics.
        """
        label = adapter.name

        example = dataset[index]
        wav_path = wav_write_fn(example, index)
        ref_raw = example.text
        audio_seconds = float(duration_fn(wav_path))

        result = adapter.transcribe(wav_path)
        hyp_raw = result.text
        process_seconds = float(result.duration_sec)

        dialogue_entries, reference_diarization = _extract_segments(result, example)
        metrics = _compute_base_wer_metrics(ref_raw, hyp_raw)
        ref_diar_dicts, hyp_diar_dicts = _process_diarization(reference_diarization, dialogue_entries, metrics)

        ref_normalized_with_speakers = format_segments_with_speakers(ref_diar_dicts) if ref_diar_dicts else ""
        hyp_normalized_with_speakers = (
            format_segments_with_speakers(hyp_diar_dicts, reference_segments=ref_diar_dicts) if hyp_diar_dicts else ""
        )

        row = SampleRow(
            engine=label,
            dataset_index=int(index),
            wav_path=wav_path,
            audio_sec=audio_seconds,
            process_sec=process_seconds,
            processing_speed_ratio=(process_seconds / audio_seconds) if audio_seconds else None,
            metrics=metrics,
            ref_raw=ref_raw,
            hyp_raw=hyp_raw,
            ref_normalized_with_speakers=ref_normalized_with_speakers,
            hyp_normalized_with_speakers=hyp_normalized_with_speakers,
        )

        with progress_bar_lock:
            progress_bar.update(1)
            progress_bar.set_postfix({"engine": label, "sample": index})

        return label, index, row, audio_seconds, process_seconds

    for adapter in adapters_config:
        results[adapter.name] = EngineResults(rows=[], timing=TimingAccumulator())

    workers = max_workers if max_workers is not None else len(adapters_config)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for adapter in adapters_config:
            for index in indices:
                future = executor.submit(process_sample, adapter, index)
                futures.append(future)

        for future in as_completed(futures):
            label, index, row, audio_seconds, process_seconds = future.result()
            results[label].rows.append(row)
            results[label].timing.add(audio_seconds, process_seconds)

    progress_bar.close()

    return [
        EngineOutput(
            summary=create_summary(
                adapter.name,
                sorted(results[adapter.name].rows, key=lambda row: row.dataset_index),
                results[adapter.name].timing,
            ),
            samples=sorted(results[adapter.name].rows, key=lambda row: row.dataset_index),
        )
        for adapter in adapters_config
    ]


def _compute_diarization_metrics(
    ref_diar: list[DiarizationSegment],
    hyp_diar: list[DiarizationSegment],
    metrics: SampleMetrics,
) -> None:
    wder_metrics = compute_wder(ref_diar, hyp_diar)
    metrics.wder = wder_metrics["wder"]
    metrics.speaker_errors = wder_metrics["speaker_errors"]
    metrics.total_words = wder_metrics["total_words"]

    speaker_metrics = compute_speaker_count_metrics(ref_diar, hyp_diar)
    metrics.speaker_count_deviation = 1.0 - speaker_metrics["speaker_count_accuracy"]
    metrics.ref_speaker_count = int(speaker_metrics["ref_speaker_count"])
    metrics.hyp_speaker_count = int(speaker_metrics["hyp_speaker_count"])
