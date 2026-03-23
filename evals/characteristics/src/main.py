import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from common.llm.client import create_chatbot
from evals.characteristics.src.types import CharacteristicExtractionOutput, EvalsConfig

"""
Characteristic Extraction evaluation pipeline.

This script processes transcripts (TXT or JSON) to extract specific characteristics
using an LLM. It handles large transcripts by chunking them with an overlap,
sanitizes input to avoid WAF issues, and maps detected characteristics back
to their original positions in the transcript.
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscriptTurn(BaseModel):
    """Represents a single turn in a conversation transcript."""

    speaker: str
    text: str


def load_config(config_path: Path) -> EvalsConfig:
    """
    Loads the evaluation configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        An EvalsConfig object containing the evaluation settings.
    """
    if not config_path.exists():
        logger.warning("Config file %s not found. Using default parameters.", config_path)
        return EvalsConfig()

    with config_path.open("r", encoding="utf-8") as f:
        raw_yaml = yaml.safe_load(f) or {}
    return EvalsConfig(**raw_yaml)


def render_prompt(template_path: str, transcript: str) -> str:
    """
    Renders a Jinja2 template with the provided transcript.

    Args:
        template_path: Path to the Jinja2 template file.
        transcript: The transcript text to include in the prompt.

    Returns:
        The rendered prompt string.
    """
    path = Path(template_path).resolve()
    env = Environment(
        loader=FileSystemLoader(path.parent),
        autoescape=select_autoescape(),
    )
    template = env.get_template(path.name)
    return template.render(transcript=transcript)


def load_transcript(file_path: Path) -> str:
    """
    Loads and formats a transcript from a file.
    Supports .txt (raw text) and .json (list of speaker/text pairs).

    Args:
        file_path: Path to the transcript file.

    Returns:
        A single string representing the full transcript.
    """
    # 1. Handle raw text as a baseline
    if file_path.suffix == ".txt":
        return file_path.read_text(encoding="utf-8")

    # 2. Assume compliant JSON (list of {speaker: ..., text: ...})
    if file_path.suffix == ".json":
        raw_data = json.loads(file_path.read_text(encoding="utf-8"))
        # Using Pydantic to validate the input structure immediately
        turns = [TranscriptTurn(**item) for item in raw_data]
        return "\n".join(f"{t.speaker}: {t.text}" for t in turns)

    message = f"Unsupported format: {file_path.suffix}"
    logger.error(message)
    raise ValueError(message)


_WAF_TRANSLATION_TABLE = str.maketrans("-\u2013\u2014", "   ", "<>*;={}()`~|")


def sanitize_for_waf(text: str) -> str:
    """
    Aggressive sanitizer to bypass Azure WAF OWASP False Positives.
    Removes characters that trigger SQLi and XSS anomaly rules.
    """
    return text.translate(_WAF_TRANSLATION_TABLE)


def deduplicate_characteristics(characteristics: list[Any]) -> list[dict[str, Any]]:
    """
    Removes duplicate characteristics based on their category and value.
    This is necessary because overlapping chunks may result in duplicate extractions.

    Args:
        characteristics: A list of characteristic objects.

    Returns:
        A list of unique characteristic dictionaries.
    """
    unique_characteristics = []
    seen_signatures = set()

    for item in characteristics:
        category = item.characteristic
        value = item.attribute_value
        signature = f"{category}|{value}"

        if signature not in seen_signatures:
            seen_signatures.add(signature)
            unique_characteristics.append(item.model_dump())

    return unique_characteristics


async def process_file(file_path: Path, config: EvalsConfig, root_dir: Path) -> dict[str, Any]:
    """
    Processes a single transcript file, extracting characteristics in chunks.

    Args:
        file_path: Path to the input transcript.
        config: Evaluation configuration.
        root_dir: The project root directory.

    Returns:
        A dictionary containing the extraction results and metadata.
    """
    prompt_rel_path = Path(config.prompts.extraction_template)
    template_name = prompt_rel_path.stem
    prompt_path = root_dir / prompt_rel_path
    model_name = config.model.model

    logger.info("Processing %s using model '%s'", file_path.name, model_name)

    transcript = load_transcript(file_path)
    chatbot = create_chatbot(
        model_type=config.model.provider,
        model_name=config.model.model,
        temperature=config.model.temperature,
    )

    # Chunking configuration: sliding window to ensure context is preserved at boundaries.
    chunk_size_chars = 1000
    overlap_chars = 250
    stride = chunk_size_chars - overlap_chars

    chunks = []
    all_detected_characteristics = []
    failed_chunks = []
    char_offsets = []

    # Split transcript into overlapping chunks
    start = 0
    while start < len(transcript):
        chunks.append(transcript[start : start + chunk_size_chars])
        char_offsets.append(start)
        start += stride

    # Process each chunk sequentially
    for idx, (chunk_text, offset) in enumerate(zip(chunks, char_offsets, strict=False)):
        logger.info("  -> Sending Chunk %d of %d to Azure...", idx + 1, len(chunks))

        # Sanitize chunk text to avoid WAF false positives (e.g., specific SQL/XSS tokens)
        safe_chunk = sanitize_for_waf(chunk_text)
        prompt_text = render_prompt(str(prompt_path), safe_chunk)
        messages = [{"role": "user", "content": prompt_text}]

        try:
            # Get structured output from the LLM
            response = await chatbot.structured_chat(messages, CharacteristicExtractionOutput)

            # Adjust indices of detected spans to match the original transcript
            for item in response.detected_characteristics:
                for span in item.evidence_spans:
                    if span.start_index is not None:
                        span.start_index += offset
                    if span.end_index is not None:
                        span.end_index += offset

                all_detected_characteristics.append(item)

            logger.info("Found %d characteristics in chunk %d", len(response.detected_characteristics), idx + 1)

        except (ValueError, RuntimeError, ConnectionError, TimeoutError) as e:
            failed_chunks.append(idx + 1)
            logger.error("     Failed on chunk %d: %s", idx + 1, e)

        # Rate limiting / polite delay between requests
        await asyncio.sleep(2)

    return {
        "version": "1.0",
        "detected_characteristics": deduplicate_characteristics(all_detected_characteristics),
        "metadata": {
            "model_used": model_name,
            "prompt_version": template_name,
            "total_chunks_processed": len(chunks),
            "failed_chunks": failed_chunks,
        },
    }


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

    # Determine project root to resolve relative paths in config
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    if not (root_dir / "pyproject.toml").exists():
        root_dir = Path.cwd()

    # Load configuration
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root_dir / config_path
    config = load_config(config_path)

    # Set up directories
    input_dir = root_dir / config.dataset.input_dir
    output_dir = root_dir / config.run.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        logger.warning(
            "Input directory not found: %s. Please add transcripts here.",
            input_dir,
        )
        return

    # Process all supported files in the input directory
    for file_path in input_dir.iterdir():
        if file_path.is_file() and file_path.suffix in [".txt", ".json"]:
            try:
                result = await process_file(file_path, config, root_dir)

                # Save results to output directory
                output_file = output_dir / f"{file_path.stem}_output.json"
                output_file.write_text(json.dumps(result, indent=2))
                logger.info("Saved result to %s", output_file)

            except (OSError, json.JSONDecodeError) as e:
                logger.error("Failed to process %s: %s", file_path, e)


if __name__ == "__main__":
    asyncio.run(main())
