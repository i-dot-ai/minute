import argparse
import logging

from adapters import AzureSTTAdapter, WhisperAdapter
from core.config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, WORKDIR
from core.dataset import audio_duration_seconds, load_benchmark_dataset, to_wav_16k_mono
from core.runner import run_engine, save_results

logger = logging.getLogger(__name__)


def run_evaluation(num_samples: int = 10, prepare_only: bool = False):
    output_dir = WORKDIR / "results"
    output_path = output_dir / "evaluation_results.json"

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
        model_name="base",
        language="en",
    )

    logger.info("Running Azure Speech-to-Text on %d samples...", len(indices))
    azure_results = run_engine(
        adapter=azure_adapter,
        indices=indices,
        label="Azure Speech-to-Text",
        dataset=ds,
        wav_write_fn=to_wav_16k_mono,
        duration_fn=audio_duration_seconds,
        is_azure=True,
    )

    logger.info("Running Whisper on %d samples...", len(indices))
    whisper_results = run_engine(
        adapter=whisper_adapter,
        indices=indices,
        label="Whisper (base)",
        dataset=ds,
        wav_write_fn=to_wav_16k_mono,
        duration_fn=audio_duration_seconds,
        is_azure=False,
    )

    save_results([azure_results, whisper_results], output_path)

    logger.info("=== Evaluation Complete ===")
    logger.info("Azure WER: %.2f%%", azure_results["summary"]["overall_wer_pct"])
    logger.info("Whisper WER: %.2f%%", whisper_results["summary"]["overall_wer_pct"])
    logger.info("Results saved to: %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Run transcription evaluation")
    parser.add_argument(
        "--num-samples",
        type=int,
        default=10,
        help="Number of meetings to evaluate from AMI dataset (default: 10)"
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
