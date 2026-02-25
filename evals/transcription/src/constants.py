from pathlib import Path

WORKDIR = Path(__file__).resolve().parent
CACHE_DIR = WORKDIR.parent / "datasets" / "ami"
AUDIO_DIR = WORKDIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)
