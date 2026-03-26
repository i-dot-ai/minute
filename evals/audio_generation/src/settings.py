import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

AUDIO_GEN_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT_DIR = AUDIO_GEN_DIR.parents[1]

INPUT_DIR = AUDIO_GEN_DIR / "input"
OUTPUT_DIR = AUDIO_GEN_DIR / "output"
CONFIG_DIR = AUDIO_GEN_DIR / "configs"
PROMPTS_DIR = AUDIO_GEN_DIR / "prompts"

config_file = CONFIG_DIR / "config.yaml"

dotenv_path = PROJECT_ROOT_DIR / ".env"
load_dotenv(dotenv_path)

with Path(config_file).open(encoding="utf-8") as f:
    _config = yaml.safe_load(f)

VOICE_MAP: dict[str, str] = _config["voices"]
DEFAULT_VOICES: list[str] = _config["default_voices"]
BACKGROUND_VOLUME_OFFSET = _config["background_volume_offset"]
TRANSCRIPT_FILE = _config["transcript_file"]
BACKGROUND_SFX_FILE = _config["background_sfx_file"]

ELEVEN_LABS_MODEL_ID = _config["eleven_labs"]["model_id"]
ELEVEN_LABS_API_KEY = os.getenv(_config["eleven_labs"]["api_key_env"])
