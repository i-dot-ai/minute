import logging
import threading
import time

import azure.cognitiveservices.speech as speechsdk

from .base import TranscriptionAdapter

logger = logging.getLogger(__name__)


class AzureSTTAdapter(TranscriptionAdapter):
    def __init__(self, speech_key: str, speech_region: str, language: str = "en-US"):
        if not speech_key or not speech_region:
            raise ValueError("Azure speech key and region are required")
        self.speech_key = speech_key
        self.speech_region = speech_region
        self.language = language

    def _make_recogniser(self, wav_path: str):
        speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.speech_region)
        speech_config.speech_recognition_language = self.language

        audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
        recogniser = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        return recogniser

    def transcribe(self, wav_path: str):
        text, proc_sec, _ = self.transcribe_with_debug(wav_path)
        return text, proc_sec

    def transcribe_with_debug(self, wav_path: str):
        recogniser = self._make_recogniser(wav_path)

        parts = []
        debug = {
            "mode": "continuous",
            "recognized_segments": [],
            "canceled": None,
            "session_stopped": False,
        }

        done = threading.Event()

        def on_recognized(evt):
            res = evt.result
            if res.reason == speechsdk.ResultReason.RecognizedSpeech and (res.text or "").strip():
                parts.append(res.text.strip())
                debug["recognized_segments"].append({
                    "text": res.text,
                    "offset": getattr(res, "offset", None),
                    "duration": getattr(res, "duration", None),
                })

        def on_canceled(evt):
            cd = speechsdk.CancellationDetails.from_result(evt.result)
            debug["canceled"] = {
                "reason": str(cd.reason),
                "error_code": str(cd.error_code),
                "error_details": cd.error_details,
            }
            done.set()

        def on_session_stopped(evt):
            debug["session_stopped"] = True
            done.set()

        recogniser.recognized.connect(on_recognized)
        recogniser.canceled.connect(on_canceled)
        recogniser.session_stopped.connect(on_session_stopped)

        t0 = time.time()
        recogniser.start_continuous_recognition_async().get()
        done.wait()
        recogniser.stop_continuous_recognition_async().get()
        t1 = time.time()

        full_text = " ".join(parts).strip()
        debug["final_text_len_chars"] = len(full_text)
        debug["final_text_len_words"] = len(full_text.split())

        return full_text, (t1 - t0), debug
