import argparse
import logging
from datetime import datetime

from adapters import AzureSTTAdapter, WhisperAdapter
from core.config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, WORKDIR
from core.dataset import audio_duration_seconds, load_benchmark_dataset, to_wav_16k_mono
from core.runner import run_engine, run_engines_parallel, save_results

logger = logging.getLogger(__name__)


def run_evaluation(num_samples: float = 10, prepare_only: bool = False):
    output_dir = WORKDIR / "results"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"evaluation_results_{timestamp}.json"

    logger.info("Loading dataset...")
    ds = load_benchmark_dataset(num_samples=num_samples)

    indices = list(range(len(ds)))
    logger.info("Loaded %d samples from AMI dataset", len(indices))
    
    if prepare_only:
        logger.info("=== Dataset Preparation Complete ===")
        logger.info("Prepared %d meetings", len(indices))
        logger.info("Audio files cached in: %s", WORKDIR / "cache" / "processed")
        return

    azure_adapter = AzureSTTAdapter(
        speech_key=AZURE_SPEECH_KEY,
        speech_region=AZURE_SPEECH_REGION,
        language="en-US",
    )

    whisper_adapter = WhisperAdapter(
        model_name="large-v3",
        language="en",
    )

    adapters_config = [
        {"adapter": azure_adapter, "label": "Azure Speech-to-Text"},
        {"adapter": whisper_adapter, "label": "Whisper"},
    ]

    logger.info("Running %d adapters in parallel on %d samples...", len(adapters_config), len(indices))
    results = run_engines_parallel(
        adapters_config=adapters_config,
        indices=indices,
        dataset=ds,
        wav_write_fn=to_wav_16k_mono,
        duration_fn=audio_duration_seconds,
    )

    save_results(results, output_path)

    logger.info("=== Evaluation Complete ===")
    for result in results:
        logger.info("%s WER: %.2f%%", result["summary"]["engine"], result["summary"]["overall_wer_pct"])
    logger.info("Results saved to: %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Run transcription evaluation")
    parser.add_argument(
        "--num-samples",
        type=float,
        default=10,
        help="Number of meetings to evaluate from AMI dataset (default: 10). "
             "If < 1.0, treated as fraction of first meeting duration (e.g., 0.1 = 10%% of first meeting)"
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only prepare and cache the dataset without running transcription"
    )
    args = parser.parse_args()

    run_evaluation(num_samples=args.num_samples, prepare_only=args.prepare_only)


if __name__ == "__main__":
    main()
