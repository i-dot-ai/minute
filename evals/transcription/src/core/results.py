import json
import logging
from pathlib import Path

from evals.transcription.src.core.metrics import aggregate_metrics
from evals.transcription.src.models import (
    AggregatedMetricStats,
    EngineOutput,
    SampleRow,
    Summary,
    TimingAccumulator,
)

logger = logging.getLogger(__name__)


def create_summary(
    label: str,
    rows: list[SampleRow],
    timing: TimingAccumulator,
) -> Summary:
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

    return Summary(
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
