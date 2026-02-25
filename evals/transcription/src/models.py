from __future__ import annotations

from typing import Callable, Protocol

import numpy
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

AudioArray = NDArray[numpy.floating]


class MeetingMetadata(BaseModel):
    """
    Metadata containing meeting IDs and their durations.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    meeting_ids: list[str]
    durations_sec: dict[str, float]


class RawAudioDict(BaseModel):
    """
    Audio representation from HuggingFace datasets.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    array: NDArray[numpy.float32]
    sampling_rate: int


class AudioSample(BaseModel):
    """
    Audio data with array, sample rate, and file path.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    array: AudioArray
    sampling_rate: int
    path: str


class DatasetItem(BaseModel):
    """
    Single dataset sample with audio and reference text.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    audio: AudioSample
    text: str


class RawDatasetRow(BaseModel):
    """
    Raw utterance row from the AMI dataset as returned by HuggingFace datasets.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    meeting_id: str
    audio_id: str
    text: str
    audio: RawAudioDict
    begin_time: float
    end_time: float
    microphone_id: str
    speaker_id: str


class Utterance(BaseModel):
    """
    Single utterance with audio, text, and timing information.
    """

    audio: dict
    text: str
    begin_time: float
    end_time: float
    meeting_id: str


class AMIDatasetSample(DatasetItem):
    """
    AMI dataset sample with meeting metadata and utterance count.
    """

    meeting_id: str
    dataset_index: int
    duration_sec: float
    num_utterances: int


class TranscriptionResult(BaseModel):
    """
    Result from a transcription operation.
    """

    text: str
    duration_sec: float
    debug_info: dict[str, object]


class DiffOps(BaseModel):
    """
    Word-level edit operations from WER calculation.
    """

    equal: int
    replace: int
    delete: int
    insert: int


class Metrics(BaseModel):
    """
    Word Error Rate metrics including edit operation counts.
    """

    wer: float
    hits: int
    substitutions: int
    deletions: int
    insertions: int


class SampleRow(BaseModel):
    """
    Detailed transcription results for a single sample.
    """

    engine: str
    dataset_index: int
    wav_path: str
    audio_sec: float
    process_sec: float
    processing_speed_ratio: float | None
    wer_pct: float
    diff_ops: DiffOps
    ref_raw: str
    hyp_raw: str
    ref_norm: str
    hyp_norm: str
    engine_debug: dict[str, object]


class Summary(BaseModel):
    """
    Aggregate metrics for a transcription engine across all samples.
    """

    engine: str
    num_samples: int
    overall_wer_pct: float
    processing_speed_ratio: float
    process_sec: float
    audio_sec: float
    per_sample_wer_min: float
    per_sample_wer_max: float
    per_sample_wer_mean: float


class EngineOutput(BaseModel):
    """
    Complete output from a transcription engine with summary and sample details.
    """

    summary: Summary
    samples: list[SampleRow]


class EngineResults(BaseModel):
    """
    Results from a transcription engine including sample rows and timing data.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    rows: list[SampleRow]
    timing: TimingAccumulator


class MeetingSegment(BaseModel):
    """
    Represents a meeting segment with optional utterance cutoff time.
    """

    meeting_id: str
    utterance_cutoff_time: float | None = None


class DatasetProtocol(Protocol):
    """
    Protocol for dataset objects supporting indexing and length operations.
    """

    def __len__(self) -> int:
        pass

    def __getitem__(self, index: int) -> DatasetItem:
        pass


class TimingAccumulator:
    """Accumulates processing and audio duration for processing speed ratio calculation."""

    def __init__(self) -> None:
        """Initializes the timing accumulator with zero values."""
        self.process_sec = 0.0
        self.audio_sec = 0.0

    def add(self, audio_sec: float, process_sec: float) -> None:
        """Adds audio and processing duration to the accumulated totals."""
        self.audio_sec += float(audio_sec)
        self.process_sec += float(process_sec)

    @property
    def processing_speed_ratio(self) -> float:
        """Calculates the ratio of processing time to audio duration."""
        return self.process_sec / self.audio_sec if self.audio_sec else float("nan")


WavWriteFn = Callable[[DatasetItem, int], str]
DurationFn = Callable[[str], float]
