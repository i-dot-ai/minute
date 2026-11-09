"""
This Module helps us detect speech before any audio is sent to a transcription provider.

FFmpeg first checks the recording's peak volume and rejects near-silent audio
without any model inference. All remaining recordings are passed
through Silero VAD v6 to detect voice.
"""

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
# Silero expects 16KHz audio with 512 samples
SAMPLE_RATE = 16000
WINDOW_SAMPLES = 512
CONTEXT_SAMPLES = 64

# Only very low peak levels bypass VAD; quiet but audible audio still reaches it.
SILENCE_MAX_VOLUME_DB = -60.0
# Silero's recommended threshold for detecting speech.
SPEECH_THRESHOLD = 0.5

_MAX_VOLUME = re.compile(r"max_volume:\s*(-?(?:inf|[\d.]+))\s*dB")


class SpeechCheckResult(StrEnum):
    """Identifies the check that determined whether speech was present."""

    VOLUME = auto()
    VAD = auto()


@dataclass(frozen=True)
class SpeechCheck:
    """Stores the outcome and measurements of a speech check.

    Attributes:
        has_speech: Whether any speech was detected.
        result: The check that produced the final outcome.
        max_volume_db: Peak audio level in dBFS, as reported by FFmpeg.
    """

    has_speech: bool
    result: SpeechCheckResult
    max_volume_db: float


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
    state separately so simultaneous checks do not share audio history.

    Returns:
        An ONNX Runtime session configured for CPU inference.
    """
    options = onnxruntime.SessionOptions()
    options.inter_op_num_threads = 1
    options.intra_op_num_threads = 1
    return onnxruntime.InferenceSession(str(MODEL_PATH), sess_options=options, providers=["CPUExecutionProvider"])


class SileroModel:
    """
    Predicts speech probabilities while keeping the recording's audio history.
    """

    def __init__(self) -> None:
        """Initialise the model with empty context and recurrent state."""
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


def contains_speech(file_path: Path) -> bool:
    """Detects any speech in streamed audio using Silero VAD.

    Args:
        file_path: Path to the local audio file.

    Returns:
        Whether any window reaches the speech threshold. Stops at the first
        detected speech window, without requiring a minimum speech duration.

    Raises:
        RuntimeError: FFmpeg fails to decode the recording.
    """
    detector = SileroModel()
    # This is the main section which actually looks for speech.
    # Essentially loop through the audio and predict speech break if True
    with decoded_audio_windows(file_path) as windows:
        for window in windows:
            if detector.predict(window) >= SPEECH_THRESHOLD:
                return True

    return False


def detect_speech(file_path: Path) -> SpeechCheck:
    """Checks for speech using peak volume followed by Silero VAD.

    Args:
        file_path: Path to the local audio file.

    Returns:
        The speech verdict, deciding check, and available audio measurements.

    Raises:
        subprocess.CalledProcessError: FFmpeg fails during the volume check.
        ValueError: FFmpeg does not report a peak level.
        RuntimeError: FFmpeg fails to decode audio for VAD.
    """
    # First get the max volume and if it's < -60DB exit because the audio is silent
    max_volume_db = get_max_volume_db(file_path)
    if max_volume_db <= SILENCE_MAX_VOLUME_DB:
        return SpeechCheck(has_speech=False, result=SpeechCheckResult.VOLUME, max_volume_db=max_volume_db)

    # If the audio is loud enough try and detect speech on it
    has_speech = contains_speech(file_path)

    return SpeechCheck(
        has_speech=has_speech,
        result=SpeechCheckResult.VAD,
        max_volume_db=max_volume_db,
    )
