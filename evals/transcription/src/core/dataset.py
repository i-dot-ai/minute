import logging
from typing import Any

import librosa
import soundfile as sf

from .ami_dataset import load_ami_dataset, audio_duration_seconds as ami_audio_duration
from .config import CACHE_DIR

logger = logging.getLogger(__name__)

TARGET_SAMPLE_RATE = 16000
STEREO_CHANNELS = 2


def load_benchmark_dataset(num_samples: float):
    logger.info("Loading AMI dataset with %d samples...", num_samples)
    logger.info("Using cache directory: %s", CACHE_DIR)
    
    ami_loader = load_ami_dataset(CACHE_DIR, num_samples)
    
    logger.info("Dataset loaded successfully")
    logger.info("Number of samples: %d", len(ami_loader))
    
    return ami_loader


def to_wav_16k_mono(example: dict[str, Any], idx: int) -> str:
    if "path" in example["audio"]:
        return example["audio"]["path"]
    
    audio = example["audio"]
    y = audio["array"]
    sr = audio["sampling_rate"]

    if getattr(y, "ndim", 1) == STEREO_CHANNELS:
        y = y.mean(axis=1)

    if sr != TARGET_SAMPLE_RATE:
        y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SAMPLE_RATE)

    from .config import AUDIO_DIR
    path = AUDIO_DIR / f"sample_{idx:06d}.wav"
    sf.write(path, y, TARGET_SAMPLE_RATE, subtype="PCM_16")
    return str(path)


def audio_duration_seconds(wav_path: str) -> float:
    return ami_audio_duration(wav_path)
