import json
import logging
from collections import defaultdict
from pathlib import Path

from datasets import load_dataset
from numpy import ndarray

from common.constants import TARGET_SAMPLE_RATE
from evals.transcription.src.core.ami import audio, cache
from evals.transcription.src.core.ami.constants import AMI_DATASET_NAME
from evals.transcription.src.core.ami.metadata import load_or_build_metadata
from evals.transcription.src.core.ami.selection import MeetingSegment, select_segments
from evals.transcription.src.models import (
    AMIDatasetSample,
    AudioSample,
    DatasetProtocol,
    RawDatasetRow,
)

logger = logging.getLogger(__name__)


def _load_utterances_for_meetings(
    required_meetings: set, split: str, config: str
) -> defaultdict[str, list[RawDatasetRow]]:
    """
    Loads specified meetings from the AMI dataset using Hugging Face's datasets library.
    Returns a dictionary mapping meeting IDs to lists of utterances.
    """
    dataset = load_dataset(AMI_DATASET_NAME, config, split=split)
    utterances_by_meeting: defaultdict[str, list[RawDatasetRow]] = defaultdict(list)
    for row in dataset:
        r = row
        meeting_id = r["meeting_id"]
        if meeting_id in required_meetings:
            utterances_by_meeting[meeting_id].append(r)
    return utterances_by_meeting


def _apply_cutoff(utterances: list[RawDatasetRow], cutoff_time: float | None) -> list[RawDatasetRow]:
    """
    Applies a cutoff time to the list of utterances, keeping only those that fit within the cutoff.
    """
    if cutoff_time is None:
        return utterances

    utterances_sorted = sorted(utterances, key=lambda x: x.begin_time)
    result: list[RawDatasetRow] = []
    accumulated = 0.0

    for utterance in utterances_sorted:
        duration = utterance.end_time - utterance.begin_time
        if accumulated + duration <= cutoff_time:
            result.append(utterance)
            accumulated += duration
        else:
            break

    return result


def _build_sample(
    mixed_audio: ndarray,
    text: str,
    segment: MeetingSegment,
    index: int,
    wav_path: Path,
    num_utterances: int,
    reference_diarization: list[dict],
) -> AMIDatasetSample:
    """
    Builds a dataset sample dictionary containing the mixed audio, transcript text, and metadata.
    """
    return AMIDatasetSample(
        audio=AudioSample(
            array=mixed_audio,
            sampling_rate=TARGET_SAMPLE_RATE,
            path=str(wav_path),
        ),
        text=text,
        meeting_id=segment.meeting_id,
        dataset_index=index,
        duration_sec=audio.compute_duration(mixed_audio),
        num_utterances=num_utterances,
        reference_diarization=reference_diarization,
    )


class AMIDatasetLoader(DatasetProtocol):
    """
    Loads and caches AMI dataset samples with configurable meeting selection.
    """

    def __init__(
        self,
        cache_dir: Path,
        num_samples: int | None,
        sample_duration_fraction: float | None = None,
        split: str = "test",
        config: str = "ihm",
    ):
        """
        Initializes the AMI dataset loader with cache directory and sampling parameters.
        """
        self.cache_dir = cache_dir
        self.num_samples = num_samples
        self.sample_duration_fraction = sample_duration_fraction
        self.split = split
        self.config = config

        self.raw_cache_dir = cache_dir / "raw"
        self.processed_cache_dir = cache_dir / "processed"

        self.raw_cache_dir.mkdir(parents=True, exist_ok=True)
        self.processed_cache_dir.mkdir(parents=True, exist_ok=True)

        self.samples: list[AMIDatasetSample] = []

    def prepare(self) -> list[AMIDatasetSample]:
        """
        Prepares the dataset by loading metadata, selecting segments, and processing audio.
        Returns a list of dataset samples ready for evaluation.
        """
        metadata = load_or_build_metadata(self.cache_dir, self.split, self.config)
        segments = select_segments(metadata, self.num_samples, self.sample_duration_fraction)

        if not segments:
            logger.warning("No segments selected")
            return []

        utterances_by_meeting = self._load_required_utterances(segments)

        for index, segment in enumerate(segments):
            sample = self._process_segment(segment, index, utterances_by_meeting)
            if sample:
                self.samples.append(sample)
                self._log_progress(index, len(segments))

        logger.info("Dataset preparation complete: %d samples ready", self.num_of_samples)
        return self.samples

    def _load_required_utterances(self, segments: list[MeetingSegment]) -> defaultdict[str, list[RawDatasetRow]]:
        """
        Checks if all required segments are already cached. If so, returns an empty dict.
        Otherwise, loads the necessary utterances for the required meetings and returns them
        in a dict.
        """
        all_cached = all(
            cache.get_cache_paths(self.processed_cache_dir, segment, index).is_complete()
            for index, segment in enumerate(segments)
        )

        if all_cached:
            logger.info("All required segments are cached, loading from cache...")
            return defaultdict(list)

        logger.info("Loading dataset for selected meetings...")
        required_meetings = {segment.meeting_id for segment in segments}
        return _load_utterances_for_meetings(required_meetings, self.split, self.config)

    def _process_segment(
        self,
        segment: MeetingSegment,
        index: int,
        utterances_by_meeting: defaultdict[str, list[RawDatasetRow]],
    ) -> AMIDatasetSample | None:
        """
        Processes a single meeting segment by either loading from cache or building from utterances.
        Returns the dataset sample for the segment, or None if processing fails.
        """
        paths = cache.get_cache_paths(self.processed_cache_dir, segment, index)
        utterances = utterances_by_meeting.get(segment.meeting_id, [])

        if paths.is_complete():
            return self._load_from_cache(utterances, paths, segment, index)

        if not utterances:
            logger.warning("No utterances for meeting %s, skipping", segment.meeting_id)
            return None

        return self._build_from_utterances(utterances, paths, segment, index)

    def _load_from_cache(
        self,
        utterances: list[RawDatasetRow],
        paths: cache.CachePaths,
        segment: MeetingSegment,
        index: int,
    ) -> AMIDatasetSample:
        """
        Loads the mixed audio and transcript text from cache and builds a dataset sample.
        """
        mixed_audio = cache.load_audio(paths.audio)
        text = cache.load_transcript(paths.transcript)

        diarization_path = paths.audio.parent / f"{paths.audio.stem}_ref_diarization.json"
        if not diarization_path.exists():
            msg = (
                f"Cache entry exists at {paths.audio} but diarization file not found at "
                f"{diarization_path}. Cache entry exists but diarization transcript is missing."
            )
            raise FileNotFoundError(msg)

        with diarization_path.open("r") as f:
            reference_diarization = json.load(f)

        word_count = len(text.split())
        sample = _build_sample(mixed_audio, text, segment, index, paths.audio, len(utterances), reference_diarization)

        logger.info(
            "Cache hit: %s (%.2f sec, %d words, %d speakers)",
            segment.meeting_id,
            sample.duration_sec,
            word_count,
            len({d["speaker"] for d in reference_diarization}) if reference_diarization else 0,
        )
        return sample

    def _build_from_utterances(
        self,
        utterances: list[RawDatasetRow],
        paths: cache.CachePaths,
        segment: MeetingSegment,
        index: int,
    ) -> AMIDatasetSample:
        """
        Builds the mixed audio and concatenated transcript text from the list of utterances,
        saves to cache, and builds a dataset sample.
        """
        utterances = _apply_cutoff(utterances, segment.utterance_cutoff_time)
        mixed_audio, text = audio.mix_utterances(utterances)

        reference_diarization: list[dict] = [
            {
                "speaker": utt.speaker_id,
                "start_time": utt.begin_time,
                "end_time": utt.end_time,
                "text": utt.text,
            }
            for utt in utterances
        ]

        cache.save_audio(paths.audio, mixed_audio, TARGET_SAMPLE_RATE)
        cache.save_transcript(paths.transcript, text)
        diarization_path = paths.audio.parent / f"{paths.audio.stem}_ref_diarization.json"
        with diarization_path.open("w") as f:
            json.dump(reference_diarization, f)

        sample = _build_sample(mixed_audio, text, segment, index, paths.audio, len(utterances), reference_diarization)

        word_count = len(text.split())
        logger.info(
            "Cache miss: mixed %s (%d utterances, %.2f sec, %d words, %d speakers)",
            segment.meeting_id,
            sample.num_utterances,
            sample.duration_sec,
            word_count,
            len({d["speaker"] for d in reference_diarization}),
        )
        return sample

    def _log_progress(self, index: int, total: int) -> None:
        """
        Logs progress every 5 segments or at the end of processing.
        """
        if (index + 1) % 5 == 0 or (index + 1) == total:
            accumulated = sum(sample.duration_sec for sample in self.samples)
            logger.info("Processed %d/%d segments, %.2f sec total", index + 1, total, accumulated)

    @property
    def num_of_samples(self) -> int:
        """
        Returns the total number of prepared samples.
        """
        return len(self.samples)

    @property
    def dataset_version(self) -> str:
        parts = ["AMI"]
        if self.num_samples is not None:
            parts.append(f"n{self.num_samples}")
        if self.sample_duration_fraction is not None:
            parts.append(f"f{self.sample_duration_fraction}")
        return "_".join(parts)

    @property
    def total_audio_sec(self) -> float:
        return sum(sample.duration_sec for sample in self.samples)

    @property
    def total_words(self) -> int:
        return sum(len(sample.text.split()) for sample in self.samples)

    def __len__(self) -> int:
        """
        Returns the number of samples in the dataset.
        """
        return self.num_of_samples

    def __getitem__(self, index: int) -> AMIDatasetSample:
        """
        Retrieves the dataset sample at the specified index.
        """
        if index < 0 or index >= self.num_of_samples:
            msg = f"Sample index {index} out of range [0, {self.num_of_samples})"
            raise IndexError(msg)
        return self.samples[index]
