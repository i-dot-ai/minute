from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypedDict

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from common.database.postgres_models import DialogueEntry

AudioArray = NDArray[np.floating]


class DiarizationSegment(TypedDict):
    speaker: str
    text: str
    start: float
    end: float


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

    array: NDArray[np.float32]
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


class AMIDatasetSample(DatasetItem):
    """
    AMI dataset sample with meeting metadata and utterance count.
    """

    meeting_id: str
    dataset_index: int
    duration_sec: float
    num_utterances: int
    reference_diarization: list[dict] = []


class TranscriptionResult(BaseModel):
    """
    Result from a transcription operation.
    """

    text: str
    duration_sec: float
    debug_info: dict[str, object]
    dialogue_entries: list[DialogueEntry] = []

    def __getitem__(self, key: str) -> object:
        return getattr(self, key)


class SampleMetrics(BaseModel):
    wer: float
    hits: int
    substitutions: int
    deletions: int
    insertions: int
    wder: float
    speaker_errors: int
    total_words: int
    speaker_count_accuracy: float
    ref_speaker_count: int
    hyp_speaker_count: int
    processing_speed_ratio: float


class SampleRow(BaseModel):
    """
    Per-example transcription eval results matching data contract schema.
    """

    run_id: str
    timestamp: str
    example_id: str
    engine_version: str
    reference_transcript: str
    reference_dialogue_entries: list[DiarizationSegment] | None
    hypothesis_transcript: str
    hypothesis_dialogue_entries: list[DiarizationSegment] | None
    latency_ms: float
    metrics: dict[str, float]
    error: dict[str, str] | None = None


class AggregatedMetricStats(BaseModel):
    mean: float
    std: float
    min: float
    max: float


class Summary(BaseModel):
    """
    Run-level transcription eval summary matching data contract schema.
    """

    run_id: str
    timestamp: str
    dataset_version: str
    engine_version: str
    split: str | None
    n_examples: int
    metrics: dict[str, AggregatedMetricStats]
    processing_speed_ratio: float


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
    """
    Accumulates processing and audio duration for processing speed ratio calculation.
    """

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
