from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

import yaml

from common.audio.ffmpeg import get_duration
from common.settings import get_settings
from evals.transcription.src.adapters.base import ServiceTranscriptionAdapter
from evals.transcription.src.adapters.registry import ADAPTER_REGISTRY
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
    adapter_names: list[str] | None = None,
) -> None:
    """
    Runs transcription evaluation on the specified dataset with configured adapters.
    """
    output_dir = WORKDIR / "output"
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    run_id = f"eval_{timestamp}"
    output_path = output_dir / f"evaluation_results_{timestamp}.json"

    logger.info("Loading dataset...")
    dataset = load_benchmark_dataset(
        num_samples=num_samples,
        sample_duration_fraction=sample_duration_fraction,
    )

    indices = list(range(len(dataset)))
    logger.info("Loaded %d samples from the dataset", len(indices))

    if prepare_only:
        logger.info("=== Dataset Preparation Complete ===")
        logger.info("Prepared %d meetings", len(indices))
        return

    if adapter_names is None:
        msg = "adapter_names is required when prepare_only is False"
        raise ValueError(msg)

    adapters = [ServiceTranscriptionAdapter(*ADAPTER_REGISTRY[name]) for name in adapter_names]

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


def load_config(config_path: Path) -> dict[str, object]:
    """
    Loads evaluation configuration from YAML file.
    """
    with config_path.open("r") as f:
        config: dict[str, object] = yaml.safe_load(f)
        return config


def main() -> None:
    """
    Parses command-line arguments and runs transcription evaluation.
    """
    parser = argparse.ArgumentParser(description="Run transcription evaluation")
    parser.add_argument(
        "--config",
        type=str,
        default="smoketest.yaml",
        help="Path to config file (default: smoketest.yaml in configs/)",
    )
    args = parser.parse_args()

    config_path = WORKDIR / "configs" / args.config
    if not config_path.exists():
        msg = f"Config file not found: {config_path}"
        raise FileNotFoundError(msg)

    config = load_config(config_path)
    logger.info("Loaded config from: %s", config_path)

    num_samples_raw = config.get("num_samples")
    sample_duration_fraction_raw = config.get("sample_duration_fraction")
    prepare_only_raw = config.get("prepare_only", False)
    max_workers_raw = config.get("max_workers")
    adapter_names_raw = config.get("adapters")

    num_samples: int | None = None
    if num_samples_raw is not None:
        if not isinstance(num_samples_raw, int):
            msg = f"Config field 'num_samples' must be an int, got {type(num_samples_raw).__name__}"
            raise TypeError(msg)
        num_samples = num_samples_raw

    sample_duration_fraction: float | None = None
    if sample_duration_fraction_raw is not None:
        if not isinstance(sample_duration_fraction_raw, int | float):
            msg = (
                f"Config field 'sample_duration_fraction' must be a number, "
                f"got {type(sample_duration_fraction_raw).__name__}"
            )
            raise TypeError(msg)
        sample_duration_fraction = float(sample_duration_fraction_raw)

    if not isinstance(prepare_only_raw, bool):
        msg = f"Config field 'prepare_only' must be a bool, got {type(prepare_only_raw).__name__}"
        raise TypeError(msg)
    prepare_only: bool = prepare_only_raw

    max_workers: int | None = None
    if max_workers_raw is not None:
        if not isinstance(max_workers_raw, int):
            msg = f"Config field 'max_workers' must be an int, got {type(max_workers_raw).__name__}"
            raise TypeError(msg)
        max_workers = max_workers_raw

    if adapter_names_raw is None:
        msg = "Required config field 'adapters' is missing"
        raise ValueError(msg)
    if not isinstance(adapter_names_raw, list):
        msg = f"Config field 'adapters' must be a list, got {type(adapter_names_raw).__name__}"
        raise TypeError(msg)
    adapter_names: list[str] = adapter_names_raw

    run_evaluation(
        num_samples=num_samples,
        sample_duration_fraction=sample_duration_fraction,
        prepare_only=prepare_only,
        max_workers=max_workers,
        adapter_names=adapter_names,
    )


if __name__ == "__main__":
    main()
