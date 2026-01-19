import logging
import time

import whisper

from .base import TranscriptionAdapter

logger = logging.getLogger(__name__)


class WhisperAdapter(TranscriptionAdapter):
    def __init__(self, model_name: str = "base", language: str = "en"):
        self.model_name = model_name
        self.language = language
        self.model = whisper.load_model(model_name)

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
            "segments": len(out.get("segments", [])),
        }

        text = out.get("text", "") or ""
        return text, (t1 - t0), debug
