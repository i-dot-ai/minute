import logging
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from evals.characteristics.src.schema import EvalsConfig

logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> EvalsConfig:
    """Loads evaluation config from a YAML file."""
    if not config_path.exists():
        logger.warning("Config file %s not found. Using default parameters.", config_path)
        return EvalsConfig()

    with config_path.open("r", encoding="utf-8") as f:
        raw_yaml = yaml.safe_load(f) or {}
    return EvalsConfig(**raw_yaml)


def render_prompt(template_path: str, transcript: str) -> str:
    """Renders a Jinja2 template with the provided transcript."""
    path = Path(template_path).resolve()
    env = Environment(
        loader=FileSystemLoader(path.parent),
        autoescape=select_autoescape(),
    )
    template = env.get_template(path.name)
    return template.render(transcript=transcript)
