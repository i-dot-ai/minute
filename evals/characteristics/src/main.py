import argparse
import asyncio
import json
import logging
from pathlib import Path

from evals.characteristics.src.config_loader import load_config
from evals.characteristics.src.pipeline import process_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Entry point for the evaluation script."""
    parser = argparse.ArgumentParser(description="Run Characteristics Extraction Evals")
    parser.add_argument(
        "--config",
        type=str,
        default="evals/characteristics/configs/default_config.yaml",
        help="Path to the YAML configuration file",
    )
    args = parser.parse_args()
    root_dir = Path(__file__).resolve().parents[3]
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root_dir / config_path
    config = load_config(config_path)

    input_dir = root_dir / config.dataset.input_dir
    output_dir = root_dir / config.run.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        logger.warning(
            "Input directory not found: %s. Please add transcripts here.",
            input_dir,
        )
        return

    for file_path in input_dir.iterdir():
        if file_path.is_file() and file_path.suffix in [".txt", ".json"]:
            try:
                result = await process_file(file_path, config, root_dir)

                output_file = output_dir / f"{file_path.stem}_output.json"
                output_file.write_text(json.dumps(result.model_dump(), indent=2))
                logger.info("Saved result to %s", output_file)

            except (OSError, json.JSONDecodeError) as e:
                logger.error("Failed to process %s: %s", file_path, e)


if __name__ == "__main__":
    asyncio.run(main())
