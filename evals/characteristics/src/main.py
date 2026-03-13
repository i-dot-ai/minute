import asyncio
import json
import logging
from pathlib import Path
from typing import Any, cast

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from common.llm.client import create_chatbot
from evals.characteristics.src.types import CharacteristicExtractionOutput

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as f:
        return cast(dict[str, Any], yaml.safe_load(f))


def render_prompt(template_path: str, transcript: str) -> str:
    path = Path(template_path).resolve()
    env = Environment(
        loader=FileSystemLoader(path.parent),
        autoescape=select_autoescape(),
    )
    template = env.get_template(path.name)
    return template.render(transcript=transcript)


def load_transcript(file_path: Path) -> str:
    if file_path.suffix == ".txt":
        return file_path.read_text(encoding="utf-8")

    if file_path.suffix == ".json":
        data = json.loads(file_path.read_text(encoding="utf-8"))

        if isinstance(data, list) and len(data) > 0 and "speaker" in data[0] and "text" in data[0]:
            # Convert DialogueEntry list to simple text
            return "\n".join(f"{item['speaker']}: {item['text']}" for item in data)

        if isinstance(data, str):
            return data

        return json.dumps(data)

    msg = f"Unsupported file format: {file_path.suffix}"
    raise ValueError(msg)


async def process_file(file_path: Path, config: dict[str, Any], root_dir: Path) -> dict[str, Any]:
    prompt_rel_path = Path(config["prompts"]["extraction_template"])
    template_name = prompt_rel_path.stem
    prompt_path = root_dir / prompt_rel_path
    model_name = config["model"]["model"]

    logger.info(
        "Processing %s using model '%s', and prompt '%s'",
        file_path,
        model_name,
        template_name,
    )

    transcript = load_transcript(file_path)
    prompt_text = render_prompt(str(prompt_path), transcript)

    chatbot = create_chatbot(
        model_type=config["model"]["provider"],
        model_name=config["model"]["model"],
        temperature=config["model"].get("temperature", 0.0),
    )

    messages = [{"role": "user", "content": prompt_text}]
    response = await chatbot.structured_chat(messages, CharacteristicExtractionOutput)

    result_dict = response.model_dump()
    result_dict["metadata"] = {
        "model_used": config["model"]["model"],
        "prompt_version": template_name,
    }

    return result_dict


async def main() -> None:
    root_dir = Path(__file__).resolve().parent.parent.parent.parent

    if not (root_dir / "pyproject.toml").exists():
        root_dir = Path.cwd()

    config_path = root_dir / "evals" / "characteristics" / "configs" / "default_config.yaml"
    config = load_config(config_path)

    input_dir = root_dir / config["dataset"]["input_dir"]
    output_dir = root_dir / config["run"]["output_dir"]
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
