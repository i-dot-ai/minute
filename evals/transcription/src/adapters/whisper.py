import logging
import time

import torch
import whisper

from .base import TranscriptionAdapter

logger = logging.getLogger(__name__)


def _get_device():
    if torch.cuda.is_available():
        device = "cuda"
        logger.info("Using CUDA for Whisper acceleration")
    elif torch.backends.mps.is_available():
        device = "mps"
        logger.info("Using MPS (Apple Silicon) for Whisper acceleration")
    else:
        device = "cpu"
        logger.info("Using CPU for Whisper (no GPU acceleration available)")
    return device


class WhisperAdapter(TranscriptionAdapter):
    def __init__(self, model_name: str = "base", language: str = "en"):
        self.model_name = model_name
        self.language = language
        self.device = _get_device()
        self.model = whisper.load_model(model_name, device=self.device)
        logger.info("Whisper model '%s' loaded on device: %s", model_name, self.device)

    def transcribe(self, wav_path: str):
        t0 = time.time()
        out = self.model.transcribe(
            wav_path,
            language=self.language,
            fp16=False,
        )
        t1 = time.time()

        text = out.get("text", "") or ""
        return text, (t1 - t0)

    def transcribe_with_debug(self, wav_path: str):
        t0 = time.time()
        out = self.model.transcribe(
            wav_path,
            language=self.language,
            fp16=False,
        )
        t1 = time.time()

        debug = {
            "model": self.model_name,
            "language": self.language,
            "device": self.device,
            "segments": len(out.get("segments", [])),
        }

        text = out.get("text", "") or ""
        return text, (t1 - t0), debug
