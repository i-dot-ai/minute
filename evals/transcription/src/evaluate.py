from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

from common.audio.ffmpeg import get_duration
from common.settings import get_settings
from evals.transcription.src.adapters import EvalsTranscriptionAdapter, azure_st_adapter, whisply_adapter
from evals.transcription.src.core.dataset import (
    load_benchmark_dataset,
    prepare_audio_for_transcription,
)
from evals.transcription.src.core.results import save_results
from evals.transcription.src.core.runner import run_engines_parallel

settings = get_settings()
WORKDIR = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)


def run_evaluation(
    num_samples: int | None = None,
    sample_duration_fraction: float | None = None,
    prepare_only: bool = False,
    max_workers: int | None = None,
) -> None:
    """
    Runs transcription evaluation on AMI dataset with Azure and Whisper adapters.
    """
    output_dir = WORKDIR / "results"
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    run_id = f"eval_{timestamp}"
    output_path = output_dir / f"evaluation_results_{timestamp}.json"

    logger.info("Loading dataset...")
    dataset = load_benchmark_dataset(
        num_samples=num_samples,
        sample_duration_fraction=sample_duration_fraction,
    )

    indices = list(range(len(dataset)))
    logger.info("Loaded %d samples from AMI dataset", len(indices))

    if prepare_only:
        logger.info("=== Dataset Preparation Complete ===")
        logger.info("Prepared %d meetings", len(indices))
        logger.info("Audio files cached in: %s", WORKDIR / "cache" / "processed")
        return

    adapters: list[EvalsTranscriptionAdapter] = [azure_st_adapter(), whisply_adapter()]

    logger.info(
        "Running %d adapters in parallel on %d samples...",
        len(adapters),
        len(indices),
    )
    results = run_engines_parallel(
        adapters=adapters,
        indices=indices,
        dataset=dataset,
        wav_write_fn=prepare_audio_for_transcription,
        duration_fn=lambda path: get_duration(Path(path)),
        run_id=run_id,
        timestamp=timestamp,
        dataset_version=dataset.dataset_version,
        dataset_split=dataset.dataset_split,
        max_workers=max_workers,
    )

    save_results(results, output_path)

    logger.info("=== Evaluation Complete ===")
    logger.info("Dataset: %s", dataset.dataset_version)
    logger.info("")
    for result in results:
        wer_pct = result.summary.metrics["wer"].mean * 100.0
        logger.info(
            "%s WER: %.2f%%",
            result.summary.engine_version,
            wer_pct,
        )
    logger.info("Results saved to: %s", output_path)


def main() -> None:
    """
    Parses command-line arguments and runs transcription evaluation.
    """
    parser = argparse.ArgumentParser(description="Run transcription evaluation")
    parser.add_argument(
        "--num-samples",
        type=int,
        default=None,
        help="Number of meetings to evaluate from AMI dataset. " "If not specified, evaluates all available meetings.",
    )
    parser.add_argument(
        "--sample-duration-fraction",
        type=float,
        default=None,
        help="Fraction of each meeting to use (e.g., 0.1 = use first 10%% of each meeting). "
        "When set, --num-samples must be >= 1.0 and specifies the number of meetings.",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only prepare and cache the dataset without running transcription",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of parallel workers. Defaults to number of adapters if not specified.",
    )
    args = parser.parse_args()

    run_evaluation(
        num_samples=args.num_samples,
        sample_duration_fraction=args.sample_duration_fraction,
        prepare_only=args.prepare_only,
        max_workers=args.max_workers,
    )


if __name__ == "__main__":
    main()
