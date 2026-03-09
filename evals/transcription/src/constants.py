from pathlib import Path

WORKDIR = Path(__file__).resolve().parent.parent
INPUT_DIR = WORKDIR / "input"
AUDIO_DIR = INPUT_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

AGGREGATABLE_METRIC_KEYS = ["wer", "wder", "speaker_count_accuracy", "processing_speed_ratio"]
