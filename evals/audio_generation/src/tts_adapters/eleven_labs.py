import logging
import typing

from elevenlabs.client import ElevenLabs

from evals.audio_generation.src.tts_adapters.base import TTSAdapter

logger = logging.getLogger(__name__)


class ElevenLabsAdapter(TTSAdapter):
    def __init__(self, api_key: str, model_id: str):
        self.client = ElevenLabs(api_key=api_key)
        self.model_id = model_id

    def text_to_speech(self, text: str, voice_id: str) -> bytes:
        audio: typing.Iterator[bytes] = self.client.text_to_speech.convert(
            text=text.strip(),
            voice_id=voice_id,
            model_id=self.model_id,
        )
        return b"".join(audio)
