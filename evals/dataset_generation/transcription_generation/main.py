import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import yaml

from evals.dataset_generation.transcription_generation.src.actor_generator import ActorGenerator
from evals.dataset_generation.transcription_generation.src.config import TranscriptGenerationConfig
from evals.dataset_generation.transcription_generation.src.transcript_generator import TranscriptGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

WORKDIR = Path(__file__).resolve().parent


async def generate_transcript_from_config(config: TranscriptGenerationConfig) -> None:
    logger.info("Starting transcript generation for theme: %s", config.theme)

    actor_generator = ActorGenerator()
    actor_definitions = await actor_generator.generate_actor_definitions(config.theme, config.num_speakers)

    transcript_generator = TranscriptGenerator(generation_config=config)
    transcript = await transcript_generator.generate_transcript(actor_definitions)

    output_dir = WORKDIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"transcript_{timestamp}.json"

    with output_path.open("w") as f:
        json.dump(
            {
                "theme": config.theme,
                "max_words": config.max_words,
                "num_speakers": config.num_speakers,
                "actor_definitions": actor_definitions,
                "dialogue_entries": [dict(entry) for entry in transcript],
            },
            f,
            indent=2,
        )

    logger.info("Transcript saved to: %s", output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic conversation transcripts")
    parser.add_argument(
        "--config",
        type=str,
        default="default.yaml",
        help="Config file name in configs/ directory (default: default.yaml)",
    )
    args = parser.parse_args()

    config_path = WORKDIR / "configs" / args.config

    if not config_path.exists():
        msg = f"Config file not found: {config_path}"
        raise FileNotFoundError(msg)

    with config_path.open() as f:
        config_data = yaml.safe_load(f)

    config = TranscriptGenerationConfig(**config_data)

    asyncio.run(generate_transcript_from_config(config))


if __name__ == "__main__":
    main()
