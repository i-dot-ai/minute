from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / "datasets" / "ami"
AUDIO_DIR = Path(__file__).resolve().parent / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

AGGREGATABLE_METRIC_KEYS = ["wer", "wder", "speaker_count_accuracy", "processing_speed_ratio"]
