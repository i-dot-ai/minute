import logging
import tempfile
from pathlib import Path

import soundfile
from common.audio.ffmpeg import convert_to_mp3

from evals.transcription.src.constants import (
    AUDIO_DIR,
    CACHE_DIR,
)
from evals.transcription.src.core.ami.loader import AMIDatasetLoader
from evals.transcription.src.core.ami_dataset import load_ami_dataset
from evals.transcription.src.models import DatasetItem

logger = logging.getLogger(__name__)


def load_benchmark_dataset(
    num_samples: int | None, sample_duration_fraction: float | None = None
) -> AMIDatasetLoader:
    """
    Loads the AMI benchmark dataset with optional sampling of meetings and duration fractions.
    """
    logger.info("Loading AMI dataset with %d samples...", num_samples)
    logger.info("Using cache directory: %s", CACHE_DIR)

    ami_loader = load_ami_dataset(CACHE_DIR, num_samples, sample_duration_fraction)

    logger.info("Dataset loaded successfully")
    logger.info("Number of samples: %d", len(ami_loader))

    return ami_loader


def prepare_audio_for_transcription(example: DatasetItem, index: int) -> str:
    """
    Converts the input audio to MP3 format using ffmpeg and caches it.
    """
    if example.audio.path and Path(example.audio.path).exists():
        return example.audio.path

    audio_data = example.audio.array
    sample_rate = example.audio.sampling_rate

    output_path = AUDIO_DIR / f"sample_{index:06d}.mp3"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        soundfile.write(temp_path, audio_data, sample_rate, subtype="PCM_16")

    try:
        convert_to_mp3(temp_path, output_path)
    finally:
        temp_path.unlink(missing_ok=True)

    return str(output_path)
