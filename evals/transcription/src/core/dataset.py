import logging
from typing import Any

import librosa
import soundfile as sf
from datasets import load_dataset

from .config import AUDIO_DIR

logger = logging.getLogger(__name__)

DATASET_NAME = "librispeech_asr"
DATASET_CONFIG = "clean"
DATASET_SPLIT = "test"

TARGET_SAMPLE_RATE = 16000
STEREO_CHANNELS = 2


def load_benchmark_dataset():
    logger.info("Loading dataset: %s %s %s", DATASET_NAME, DATASET_CONFIG, DATASET_SPLIT)
    logger.info("This may take a while on first run (downloading dataset)...")
    
    ds = load_dataset(DATASET_NAME, DATASET_CONFIG, split=DATASET_SPLIT)
    
    logger.info("Dataset loaded successfully")
    logger.info("Number of rows: %d", len(ds))

    _validate_dataset_contract(ds)
    return ds


def _validate_dataset_contract(ds):
    ex0 = ds[0]

    assert "audio" in ex0, "Dataset row must contain 'audio'"
    assert "text" in ex0, "Dataset row must contain 'text'"
    assert "array" in ex0["audio"], "audio must contain 'array'"
    assert "sampling_rate" in ex0["audio"], "audio must contain 'sampling_rate'"
    assert isinstance(ex0["text"], str), "'text' must be a string transcript"

    audio_array = ex0["audio"]["array"]
    sampling_rate = ex0["audio"]["sampling_rate"]

    logger.info("Dataset contract check passed.")
    logger.debug("Example text type: %s", type(ex0["text"]))
    logger.debug("Audio array ndim: %s", getattr(audio_array, "ndim", None))
    logger.debug("Audio array shape: %s", getattr(audio_array, "shape", None))
    logger.debug("Sampling rate: %d", sampling_rate)


def to_wav_16k_mono(example: dict[str, Any], idx: int) -> str:
    audio = example["audio"]
    y = audio["array"]
    sr = audio["sampling_rate"]

    if getattr(y, "ndim", 1) == STEREO_CHANNELS:
        y = y.mean(axis=1)

    if sr != TARGET_SAMPLE_RATE:
        y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SAMPLE_RATE)

    path = AUDIO_DIR / f"sample_{idx:06d}.wav"
    sf.write(path, y, TARGET_SAMPLE_RATE, subtype="PCM_16")
    return str(path)


def audio_duration_seconds(wav_path: str) -> float:
    y, sr = librosa.load(wav_path, sr=None, mono=True)
    return float(len(y) / sr)
