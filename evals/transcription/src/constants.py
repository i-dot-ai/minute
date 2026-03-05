from pathlib import Path

WORKDIR = Path(__file__).resolve().parent.parent
INPUT_DIR = WORKDIR / "input"
AUDIO_DIR = INPUT_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
