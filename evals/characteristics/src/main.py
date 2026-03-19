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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscriptTurn(BaseModel):
    speaker: str
    text: str


def load_config(config_path: Path) -> EvalsConfig:
    if not config_path.exists():
        logger.warning("Config file %s not found. Using default parameters.", config_path)
        return EvalsConfig()  # Uses the Pydantic defaults automatically!

    with config_path.open("r", encoding="utf-8") as f:
        raw_yaml = yaml.safe_load(f) or {}

    # Pydantic will automatically raise detailed errors if the YAML has bad types
    return EvalsConfig(**raw_yaml)


def render_prompt(template_path: str, transcript: str) -> str:
    path = Path(template_path).resolve()
    env = Environment(
        loader=FileSystemLoader(path.parent),
        autoescape=select_autoescape(),
    )
    template = env.get_template(path.name)
    return template.render(transcript=transcript)


def load_transcript(file_path: Path) -> str:
    # 1. Handle raw text as a baseline
    if file_path.suffix == ".txt":
        return file_path.read_text(encoding="utf-8")

    # 2. Assume compliant JSON
    if file_path.suffix == ".json":
        raw_data = json.loads(file_path.read_text(encoding="utf-8"))
        # Using Pydantic to validate the input structure immediately
        turns = [TranscriptTurn(**item) for item in raw_data]
        return "\n".join(f"{t.speaker}: {t.text}" for t in turns)

    raise ValueError(f"Unsupported format: {file_path.suffix}")


_WAF_TRANSLATION_TABLE = str.maketrans("-–—", "   ", "<>*;={}()`~|")  # noqa: RUF001


def sanitize_for_waf(text: str) -> str:
    """
    Aggressive sanitizer to bypass Azure WAF OWASP False Positives.
    Removes characters that trigger SQLi and XSS anomaly rules.
    """
    return text.translate(_WAF_TRANSLATION_TABLE)


async def process_file(file_path: Path, config: EvalsConfig, root_dir: Path) -> dict[str, Any]:
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

    # 3. Small Text Chunking for MAXIMUM RECALL (High Detail)
    chunk_size_chars = 1000

    all_detected_characteristics = []
    chunks = []
    failed_chunks = []

    for idx, char_offset in enumerate(range(0, len(transcript), chunk_size_chars)):
        chunk_text = transcript[char_offset : char_offset + chunk_size_chars]
        chunks.append(chunk_text)

        logger.info("  -> Sending Chunk %d to Azure...", idx + 1)

        # Scrub WAF triggers
        safe_chunk = sanitize_for_waf(chunk_text)

        prompt_text = render_prompt(str(prompt_path), safe_chunk)
        messages = [{"role": "user", "content": prompt_text}]

        try:
            response = await chatbot.structured_chat(messages, CharacteristicExtractionOutput)
            for item in response.detected_characteristics:
                for span in item.evidence_spans:
                    if span.start_index is not None:
                        span.start_index += char_offset
                    if span.end_index is not None:
                        span.end_index += char_offset

                all_detected_characteristics.append(item)

            logger.info("     Found %d characteristics in chunk %d", len(response.detected_characteristics), idx + 1)
        except Exception as e:  # noqa: BLE001
            failed_chunks.append(idx + 1)
            logger.error("     Failed on chunk %d: %s", idx + 1, e)

    # Deduplicate the results
    unique_characteristics = []
    seen_signatures = set()

    for item in all_detected_characteristics:
        category = item.characteristic
        value = item.attribute_value

        signature = f"{category}|{value}"

        if signature not in seen_signatures:
            seen_signatures.add(signature)
            unique_characteristics.append(item.model_dump())
        else:
            pass

    # 5. Aggregate the results into final data contract

    return {
        "version": "1.0",
        "detected_characteristics": unique_characteristics,
        "metadata": {
            "model_used": config.model.model,
            "prompt_version": template_name,
            "total_chunks_processed": len(chunks),
            "failed_chunks": failed_chunks,
        },
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run Characteristics Extraction Evals")
    parser.add_argument(
        "--config",
        type=str,
        default="evals/characteristics/configs/default_config.yaml",
        help="Path to the YAML configuration file",
    )
    args = parser.parse_args()
    root_dir = Path(__file__).resolve().parent.parent.parent.parent

    if not (root_dir / "pyproject.toml").exists():
        root_dir = Path.cwd()

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
                output_file.write_text(json.dumps(result, indent=2))
                logger.info("Saved result to %s", output_file)
            except (OSError, json.JSONDecodeError) as e:
                logger.error("Failed to process %s: %s", file_path, e)


if __name__ == "__main__":
    asyncio.run(main())
