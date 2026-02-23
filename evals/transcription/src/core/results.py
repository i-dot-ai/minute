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
    run_id: str,
    timestamp: str,
    dataset_version: str,
    dataset_split: str | None,
) -> Summary:
    metrics_list = [row.metrics for row in rows]
    aggregated_dict = aggregate_metrics(metrics_list)
    aggregated = {key: AggregatedMetricStats(**stats) for key, stats in aggregated_dict.items()}

    overall_score = 1.0 - aggregated["wer"].mean if "wer" in aggregated else None

    return Summary(
        run_id=run_id,
        timestamp=timestamp,
        dataset_version=dataset_version,
        engine_version=label,
        split=dataset_split,
        n_examples=len(rows),
        overall_score=overall_score,
        metrics=aggregated,
        processing_speed_ratio=timing.processing_speed_ratio,
    )


def save_results(
    results: list[EngineOutput],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    combined = {
        "summaries": [result.summary.model_dump() for result in results],
        "engines": {result.summary.engine_version: [s.model_dump() for s in result.samples] for result in results},
    }

    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(combined, file_handle, indent=2, ensure_ascii=False)

    logger.info("Results saved to %s", output_path)
