"""
This Module helps us detect speech before any audio is sent to a transcription provider.

FFmpeg first checks the recording's peak volume and rejects near-silent audio
without any model inference. All remaining recordings are passed
through Silero VAD v6 to detect voice.
"""

import math
import re
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum, auto
from functools import cache
from pathlib import Path
from typing import BinaryIO

import numpy as np
import onnxruntime
from numpy.typing import NDArray

# The Silero VAD model https://github.com/snakers4/silero-vad
MODEL_PATH = Path(__file__).parent / "models" / "silero_vad.onnx"
SAMPLE_RATE = 16000
# At 16 kHz, the model expects 32 ms windows prefixed with 64 context samples.
WINDOW_SAMPLES = 512
CONTEXT_SAMPLES = 64

# Only very low peak levels bypass VAD; quiet but audible audio still reaches it.
SILENCE_MAX_VOLUME_DB = -60.0
# Silero's recommended thresholds: enter speech at 0.5, leave it below 0.35.
SPEECH_THRESHOLD = 0.5
LEAVING_SPEECH_THRESHOLD = 0.35
# Discard short detections to reduce false positives from clicks and noise bursts.
MIN_SPEECH_RUN_SECONDS = 0.25
# Total speech needed to send the recording on to transcription.
MIN_SPEECH_SECONDS = 1.0

_MAX_VOLUME = re.compile(r"max_volume:\s*(-?(?:inf|[\d.]+))\s*dB")


class SpeechCheckTier(StrEnum):
    """Identifies the check that determined whether speech was present."""

    VOLUME = auto()
    VAD = auto()


@dataclass(frozen=True)
class SpeechCheck:
    """Stores the outcome and measurements of a speech check.

    Attributes:
        has_speech: Whether enough speech was detected to allow transcription.
        tier: The check that produced the final outcome.
        max_volume_db: Peak audio level in dBFS, as reported by FFmpeg.
        speech_seconds: Confirmed speech duration. Zero when VAD was skipped.
            Early stopping means this is not necessarily the full duration.
    """

    has_speech: bool
    tier: SpeechCheckTier
    max_volume_db: float
    speech_seconds: float = 0.0


def get_max_volume_db(file_path: Path) -> float:
    """Measures a recording's peak audio level using FFmpeg.

    Args:
        file_path: Path to the local audio file.

    Returns:
        Peak level in dBFS. FFmpeg may report a finite floor for digital silence.

    Raises:
        subprocess.CalledProcessError: FFmpeg cannot process the audio.
        ValueError: FFmpeg does not report a peak level.
    """
    result = subprocess.run(  # noqa: S603
        ["ffmpeg", "-nostdin", "-hide_banner", "-i", str(file_path), "-af", "volumedetect", "-f", "null", "-"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    match = _MAX_VOLUME.search(result.stderr)
    if not match:
        msg = "ffmpeg volumedetect reported no max_volume"
        raise ValueError(msg)
    return float(match.group(1))


@cache
def _get_model_session() -> onnxruntime.InferenceSession:
    """Returns a cached CPU inference session for the vendored Silero model.

    Inference uses one thread per session. Each recording keeps its recurrent
    state separately so concurrent checks do not share audio history.

    Returns:
        An ONNX Runtime session configured for CPU inference.
    """
    options = onnxruntime.SessionOptions()
    options.inter_op_num_threads = 1
    options.intra_op_num_threads = 1
    return onnxruntime.InferenceSession(str(MODEL_PATH), sess_options=options, providers=["CPUExecutionProvider"])


class SileroModel:
    """Predicts speech probabilities while keeping one recording's audio history.

    Model weights are shared through a cached session. Context and recurrent
    state belong to each instance, so concurrent recordings remain independent.
    """

    def __init__(self) -> None:
        """Initializes the model with empty context and recurrent state."""
        self._session = _get_model_session()
        self._sample_rate = np.array(SAMPLE_RATE, dtype=np.int64)
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, CONTEXT_SAMPLES), dtype=np.float32)

    def predict(self, window: NDArray[np.float32]) -> float:
        """Predicts the speech probability for the next audio window.

        Args:
            window: A one-dimensional array of WINDOW_SAMPLES audio samples.
                Windows must be supplied in recording order.

        Returns:
            The model's speech probability for this window.
        """
        model_input = np.concatenate([self._context, window[np.newaxis, :]], axis=1)
        output, self._state = self._session.run(
            None, {"input": model_input, "state": self._state, "sr": self._sample_rate}
        )
        self._context = model_input[:, -CONTEXT_SAMPLES:]
        return float(output[0, 0])


class SpeechCounter:
    """Counts speech windows while rejecting short detection runs.

    Attributes:
        speech_seconds: Confirmed duration, including a qualifying current run.
    """

    def __init__(self) -> None:
        """Initializes an empty counter using the configured speech thresholds."""
        self._window_seconds = WINDOW_SAMPLES / SAMPLE_RATE
        self._min_run_windows = math.ceil(MIN_SPEECH_RUN_SECONDS / self._window_seconds)
        self._speech_windows = 0
        self._run_windows = 0

    def update(self, probability: float) -> None:
        """Updates the counter with the next window's speech probability.

        Args:
            probability: Speech probability for the next consecutive window.
        """
        # The lower exit threshold prevents borderline scores from fragmenting speech.
        if probability >= SPEECH_THRESHOLD or (self._run_windows and probability >= LEAVING_SPEECH_THRESHOLD):
            self._run_windows += 1
        else:
            if self._run_windows >= self._min_run_windows:
                self._speech_windows += self._run_windows
            self._run_windows = 0

    @property
    def speech_seconds(self) -> float:
        """Returns confirmed speech duration, excluding runs that are too short."""
        current_windows = self._run_windows if self._run_windows >= self._min_run_windows else 0
        return (self._speech_windows + current_windows) * self._window_seconds


def _iter_audio_windows(stream: BinaryIO) -> Iterator[NDArray[np.float32]]:
    """Splits decoded Float32 audio into fixed-size model input windows.

    Args:
        stream: A buffered stream of mono Float32 audio at SAMPLE_RATE.

    Yields:
        Consecutive windows of WINDOW_SAMPLES samples. The final window is
        padded with zeros if needed.
    """
    # Read approximately eight seconds at a time. Float32 samples use four bytes.
    while chunk := stream.read(WINDOW_SAMPLES * 4 * 256):
        samples = np.frombuffer(chunk[: len(chunk) - len(chunk) % 4], dtype=np.float32)
        for start in range(0, len(samples), WINDOW_SAMPLES):
            window = samples[start : start + WINDOW_SAMPLES]
            if len(window) < WINDOW_SAMPLES:
                window = np.pad(window, (0, WINDOW_SAMPLES - len(window)))
            yield window


@contextmanager
def decoded_audio_windows(file_path: Path) -> Iterator[Iterator[NDArray[np.float32]]]:
    """Opens an audio-window iterator and manages the FFmpeg decoder's lifetime.

    Args:
        file_path: Path to the local audio file.

    Yields:
        An iterator of 16 kHz mono Float32 windows suitable for Silero inference.

    Raises:
        RuntimeError: FFmpeg fails after the audio iterator is exhausted.
    """
    command = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(file_path)]
    command += ["-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"]
    # A file prevents decoder diagnostics from filling a pipe and blocking audio output.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)  # noqa: S603
        try:
            assert process.stdout is not None  # noqa: S101
            with process.stdout:
                yield _iter_decoded_windows(process, errors)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()


def _iter_decoded_windows(process: subprocess.Popen, errors: BinaryIO) -> Iterator[NDArray[np.float32]]:
    """Yields decoder output and checks for failures when the stream ends.

    Args:
        process: The running FFmpeg decoder with piped standard output.
        errors: Seekable file containing the decoder's diagnostic output.

    Yields:
        Consecutive audio windows from the decoder.

    Raises:
        RuntimeError: FFmpeg exits unsuccessfully after its output is exhausted.
    """
    assert process.stdout is not None  # noqa: S101
    yield from _iter_audio_windows(process.stdout)
    # Early stopping never reaches this check; the context manager kills the decoder.
    if process.wait() != 0:
        errors.seek(0)
        details = errors.read().decode(errors="replace").strip()
        msg = f"ffmpeg failed to decode audio for speech detection: {details}"
        raise RuntimeError(msg)


def count_speech_seconds(file_path: Path, stop_after_seconds: float = MIN_SPEECH_SECONDS) -> float:
    """Counts confirmed speech in streamed audio using Silero VAD.

    Args:
        file_path: Path to the local audio file.
        stop_after_seconds: Speech duration at which inference stops early.
            Use float("inf") to process the entire recording.

    Returns:
        Confirmed speech duration in seconds, measured in 32 ms windows. The
        result may exceed stop_after_seconds by part of one window.

    Raises:
        RuntimeError: FFmpeg fails to decode the recording.
    """
    detector = SileroModel()
    counter = SpeechCounter()

    with decoded_audio_windows(file_path) as windows:
        for window in windows:
            probability = detector.predict(window)
            counter.update(probability)

            if counter.speech_seconds >= stop_after_seconds:
                break

    return counter.speech_seconds


def detect_speech(file_path: Path) -> SpeechCheck:
    """Checks for speech using peak volume followed by Silero VAD.

    Args:
        file_path: Path to the local audio file.

    Returns:
        The speech verdict, deciding tier, and available audio measurements.

    Raises:
        subprocess.CalledProcessError: FFmpeg fails during the volume check.
        ValueError: FFmpeg does not report a peak level.
        RuntimeError: FFmpeg fails to decode audio for VAD.
    """
    max_volume_db = get_max_volume_db(file_path)
    if max_volume_db <= SILENCE_MAX_VOLUME_DB:
        return SpeechCheck(has_speech=False, tier=SpeechCheckTier.VOLUME, max_volume_db=max_volume_db)
    speech_seconds = count_speech_seconds(file_path)
    return SpeechCheck(
        has_speech=speech_seconds >= MIN_SPEECH_SECONDS,
        tier=SpeechCheckTier.VAD,
        max_volume_db=max_volume_db,
        speech_seconds=speech_seconds,
    )
