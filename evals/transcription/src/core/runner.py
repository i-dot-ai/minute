import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

import numpy
from tqdm import tqdm

from evals.transcription.src.adapters.base import AdapterConfig
from evals.transcription.src.core.metrics import compute_wer_metrics, normalise_text
from evals.transcription.src.models import (
    DatasetProtocol,
    DiffOps,
    DurationFn,
    EngineOutput,
    EngineResults,
    SampleRow,
    Summary,
    TimingAccumulator,
    WavWriteFn,
)

logger = logging.getLogger(__name__)


def run_engines_parallel(
    adapters_config: list[AdapterConfig],
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
        adapter_config: AdapterConfig,
        index: int,
    ) -> tuple[str, int, SampleRow, float, float]:
        """
        Transcribes a single sample and computes WER metrics.
        """
        adapter = adapter_config["adapter"]
        label = adapter.name

        example = dataset[int(index)]
        wav_path = wav_write_fn(example, int(index))
        ref_raw = example.text
        audio_seconds = float(duration_fn(wav_path))

        result = adapter.transcribe(wav_path)
        hyp_raw = result.text
        process_seconds = float(result.duration_sec)
        debug_info = result.debug_info

        reference_normalized = normalise_text(ref_raw)
        hypothesis_normalized = normalise_text(hyp_raw)
        per_metrics = compute_wer_metrics([reference_normalized], [hypothesis_normalized])
        per_sample_wer = per_metrics.wer * 100.0
        diff_operations = DiffOps(
            equal=per_metrics.hits,
            replace=per_metrics.substitutions,
            delete=per_metrics.deletions,
            insert=per_metrics.insertions,
        )

        row = SampleRow(
            engine=label,
            dataset_index=int(index),
            wav_path=wav_path,
            audio_sec=audio_seconds,
            process_sec=process_seconds,
            processing_speed_ratio=(process_seconds / audio_seconds) if audio_seconds else None,
            wer_pct=float(per_sample_wer),
            diff_ops=diff_operations,
            ref_raw=ref_raw,
            hyp_raw=hyp_raw,
            ref_norm=reference_normalized,
            hyp_norm=hypothesis_normalized,
            engine_debug=debug_info,
        )

        with progress_bar_lock:
            progress_bar.update(1)
            progress_bar.set_postfix({"engine": label, "sample": index})

        return label, index, row, audio_seconds, process_seconds

    for adapter_config in adapters_config:
        results[adapter_config["adapter"].name] = EngineResults(rows=[], timing=TimingAccumulator())

    workers = max_workers if max_workers is not None else len(adapters_config)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for adapter_config in adapters_config:
            for index in indices:
                future = executor.submit(process_sample, adapter_config, index)
                futures.append(future)

        for future in as_completed(futures):
            label, index, row, audio_seconds, process_seconds = future.result()
            results[label].rows.append(row)
            results[label].timing.add(audio_seconds, process_seconds)

    progress_bar.close()

    output_results: list[EngineOutput] = []
    for adapter_config in adapters_config:
        label = adapter_config["adapter"].name
        rows = sorted(results[label].rows, key=lambda row: row.dataset_index)
        timing = results[label].timing

        overall_metrics = compute_wer_metrics(
            [row.ref_raw for row in rows],
            [row.hyp_raw for row in rows],
        )
        overall_wer = overall_metrics.wer * 100.0
        per_sample_wers = [row.wer_pct for row in rows]

        summary = Summary(
            engine=label,
            num_samples=len(indices),
            overall_wer_pct=float(overall_wer),
            processing_speed_ratio=float(timing.processing_speed_ratio),
            process_sec=float(timing.process_sec),
            audio_sec=float(timing.audio_sec),
            per_sample_wer_min=float(numpy.min(per_sample_wers)),
            per_sample_wer_max=float(numpy.max(per_sample_wers)),
            per_sample_wer_mean=float(numpy.mean(per_sample_wers)),
        )

        output_results.append(EngineOutput(summary=summary, samples=rows))

    return output_results


def save_results(results: list[EngineOutput], output_path: Path) -> None:
    """
    Saves evaluation results to JSON file with summaries and per-sample details.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    combined = {
        "summaries": [result.summary.model_dump() for result in results],
        "engines": {
            result.summary.engine: [s.model_dump() for s in result.samples] for result in results
        },
    }

    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(combined, file_handle, indent=2, ensure_ascii=False)

    logger.info("Results saved to %s", output_path)
