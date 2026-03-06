from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

import yaml

from common.audio.ffmpeg import get_duration
from common.settings import get_settings
from evals.transcription.src.adapters.base import AdapterConfig, ServiceTranscriptionAdapter
from evals.transcription.src.adapters.registry import ADAPTER_REGISTRY
from evals.transcription.src.core.dataset import (
    load_benchmark_dataset,
    prepare_audio_for_transcription,
)
from evals.transcription.src.core.runner import run_engines_parallel, save_results

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
    Runs transcription evaluation on AMI dataset with configured adapters.
    """
    output_dir = WORKDIR / "results"
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
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
        logger.info("Audio files cached in: %s", WORKDIR / "input" / "ami" / "processed")
        return

    if adapter_names is None:
        adapter_names = list(ADAPTER_REGISTRY.keys())

    if not adapter_names:
        msg = "No adapters specified in config"
        raise ValueError(msg)

    adapters_config: list[AdapterConfig] = [
        {"adapter": ServiceTranscriptionAdapter(adapter_class, adapter_name)}
        for name in adapter_names
        for adapter_class, adapter_name in [ADAPTER_REGISTRY[name]]
    ]
    logger.info("Using adapters: %s", ", ".join(adapter_names))

    logger.info(
        "Running %d adapters in parallel on %d samples...",
        len(adapters_config),
        len(indices),
    )
    results = run_engines_parallel(
        adapters_config=adapters_config,
        indices=indices,
        dataset=dataset,
        wav_write_fn=prepare_audio_for_transcription,
        duration_fn=lambda path: get_duration(Path(path)),
        max_workers=max_workers,
    )

    save_results(results, output_path)

    logger.info("=== Evaluation Complete ===")
    for result in results:
        logger.info(
            "%s WER: %.2f%%",
            result.summary.engine,
            result.summary.overall_wer_pct,
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
        default="default.yaml",
        help="Path to config file (default: default.yaml in configs/)",
    )
    args = parser.parse_args()

    config_path = WORKDIR / "configs" / args.config
    if not config_path.exists():
        msg = f"Config file not found: {config_path}"
        raise FileNotFoundError(msg)

    config = load_config(config_path)
    logger.info("Loaded config from: %s", config_path)

    num_samples = config.get("num_samples")
    sample_duration_fraction = config.get("sample_duration_fraction")
    prepare_only = config.get("prepare_only", False)
    max_workers = config.get("max_workers")
    adapter_names = config.get("adapters")

    run_evaluation(
        num_samples=int(num_samples) if num_samples is not None else None,  # type: ignore[call-overload]
        sample_duration_fraction=float(sample_duration_fraction) if sample_duration_fraction is not None else None,  # type: ignore[arg-type]
        prepare_only=bool(prepare_only),
        max_workers=int(max_workers) if max_workers is not None else None,  # type: ignore[call-overload]
        adapter_names=list(adapter_names) if adapter_names is not None else None,  # type: ignore[call-overload]
    )


if __name__ == "__main__":
    main()
