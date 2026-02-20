import json
import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from tqdm import tqdm

from evals.transcription.src.adapters.base import EvalsTranscriptionAdapter
from evals.transcription.src.core.formatting import format_segments_with_speakers
from evals.transcription.src.core.metrics import (
    aggregate_metrics,
    compute_speaker_count_metrics,
    compute_wder,
    compute_wer_metrics,
    normalise_text,
)
from evals.transcription.src.models import (
    AggregatedMetricStats,
    DatasetProtocol,
    DiarizationSegment,
    DurationFn,
    EngineOutput,
    EngineResults,
    SampleMetrics,
    SampleRow,
    Summary,
    TimingAccumulator,
    WavWriteFn,
)

logger = logging.getLogger(__name__)


def run_engines_parallel(  # noqa: PLR0915
    adapters_config: Sequence[EvalsTranscriptionAdapter],
    indices: list[int],
    *,
    dataset: DatasetProtocol,
    wav_write_fn: WavWriteFn,
    duration_fn: DurationFn,
    max_workers: int | None = None,
) -> list[EngineOutput]:
    total_tasks = len(indices) * len(adapters_config)
    progress_bar = tqdm(total=total_tasks, desc="Processing all engines", unit="task")
    progress_bar_lock = Lock()

    results: dict[str, EngineResults] = {}

    def process_sample(
        adapter: EvalsTranscriptionAdapter,
        index: int,
    ) -> tuple[str, int, SampleRow, float, float]:
        label = adapter.name

        example = dataset[int(index)]
        wav_path = wav_write_fn(example, int(index))
        ref_raw = example.text
        audio_seconds = float(duration_fn(wav_path))

        result = adapter.transcribe(wav_path)
        hyp_raw = result.text
        process_seconds = float(result.duration_sec)

        dialogue_entries = result.dialogue_entries if hasattr(result, "dialogue_entries") else []
        reference_diarization = example.reference_diarization if hasattr(example, "reference_diarization") else []

        reference_normalized = normalise_text(ref_raw)
        hypothesis_normalized = normalise_text(hyp_raw)

        wer_metrics = compute_wer_metrics([reference_normalized], [hypothesis_normalized])

        metrics = SampleMetrics(
            wer=wer_metrics.wer,
            hits=wer_metrics.hits,
            substitutions=wer_metrics.substitutions,
            deletions=wer_metrics.deletions,
            insertions=wer_metrics.insertions,
        )

        ref_diar_dicts: list[DiarizationSegment] = []
        hyp_diar_dicts: list[DiarizationSegment] = []

        if reference_diarization and dialogue_entries:
            ref_diar_dicts = _convert_to_diarization_format(reference_diarization)
            hyp_diar_dicts = _convert_to_diarization_format(dialogue_entries)
            wder_metrics = compute_wder(ref_diar_dicts, hyp_diar_dicts)
            metrics.wder = wder_metrics["wder"]
            metrics.speaker_errors = wder_metrics["speaker_errors"]
            metrics.total_words = wder_metrics["total_words"]

            speaker_metrics = compute_speaker_count_metrics(ref_diar_dicts, hyp_diar_dicts)
            metrics.speaker_count_deviation = 1.0 - speaker_metrics["speaker_count_accuracy"]
            metrics.ref_speaker_count = int(speaker_metrics["ref_speaker_count"])
            metrics.hyp_speaker_count = int(speaker_metrics["hyp_speaker_count"])

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

    output_results: list[EngineOutput] = []
    for adapter in adapters_config:
        label = adapter.name
        rows = sorted(results[label].rows, key=lambda row: row.dataset_index)
        timing = results[label].timing

        metrics_list = [row.metrics.model_dump() for row in rows]
        aggregated_dict = aggregate_metrics(metrics_list)

        aggregated = {key: AggregatedMetricStats(**stats) for key, stats in aggregated_dict.items()}

        total_hits = sum(row.metrics.hits for row in rows)
        total_substitutions = sum(row.metrics.substitutions for row in rows)
        total_deletions = sum(row.metrics.deletions for row in rows)
        total_insertions = sum(row.metrics.insertions for row in rows)
        total_speaker_errors = sum(row.metrics.speaker_errors or 0 for row in rows)

        speaker_count_deviations = [
            row.metrics.speaker_count_deviation for row in rows if row.metrics.speaker_count_deviation is not None
        ]
        speaker_count_accuracy = (
            1.0 - (sum(speaker_count_deviations) / len(speaker_count_deviations)) if speaker_count_deviations else 0.0
        )

        overall_wer_pct = aggregated["wer"].mean * 100.0 if "wer" in aggregated else 0.0

        summary = Summary(
            engine=label,
            num_samples=len(rows),
            overall_wer_pct=float(overall_wer_pct),
            processing_speed_ratio=float(timing.processing_speed_ratio),
            process_sec=float(timing.process_sec),
            audio_sec=float(timing.audio_sec),
            aggregated_metrics=aggregated,
            speaker_count_accuracy=speaker_count_accuracy,
            total_hits=total_hits,
            total_substitutions=total_substitutions,
            total_deletions=total_deletions,
            total_insertions=total_insertions,
            total_speaker_errors=total_speaker_errors,
        )

        output_results.append(EngineOutput(summary=summary, samples=rows))

    return output_results


def _convert_to_diarization_format(segments: list) -> list[DiarizationSegment]:
    result: list[DiarizationSegment] = []
    for seg in segments:
        if isinstance(seg, dict):
            result.append(
                {
                    "speaker": seg.get("speaker", ""),
                    "text": seg.get("text", ""),
                    "start": float(seg.get("start", 0.0) or seg.get("start_time", 0.0)),
                    "end": float(seg.get("end", 0.0) or seg.get("end_time", 0.0)),
                }
            )
        else:
            result.append(
                {
                    "speaker": getattr(seg, "speaker", ""),
                    "text": getattr(seg, "text", ""),
                    "start": float(getattr(seg, "start", 0.0) or getattr(seg, "start_time", 0.0)),
                    "end": float(getattr(seg, "end", 0.0) or getattr(seg, "end_time", 0.0)),
                }
            )
    return result


def save_results(
    results: list[EngineOutput],
    output_path: Path,
    run_info: dict[str, float | int | str],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    combined = {
        "run_info": run_info,
        "summaries": [result.summary.model_dump() for result in results],
        "engines": {result.summary.engine: [s.model_dump() for s in result.samples] for result in results},
    }

    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(combined, file_handle, indent=2, ensure_ascii=False)

    logger.info("Results saved to %s", output_path)
