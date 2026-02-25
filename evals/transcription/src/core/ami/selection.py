import logging

from evals.transcription.src.models import MeetingMetadata, MeetingSegment

logger = logging.getLogger(__name__)


def select_segments(
    metadata: MeetingMetadata,
    num_samples: int | None,
    sample_duration_fraction: float | None = None,
) -> list[MeetingSegment]:
    """
    Selects meeting segments based on the provided metadata, number of samples, and optional
    duration fraction. Returns a list of MeetingSegment objects representing the selected
    segments for evaluation.
    """
    meeting_ids = metadata.meeting_ids
    durations = metadata.durations_sec

    if not meeting_ids:
        return []

    num_meetings = len(meeting_ids) if num_samples is None else num_samples

    if sample_duration_fraction is not None:
        logger.info(
            "Selecting first %d meetings with %.1f%% duration each",
            num_meetings,
            sample_duration_fraction * 100,
        )

        segments = []
        for meeting_id in meeting_ids[:num_meetings]:
            meeting_duration = durations.get(meeting_id, 0)
            cutoff_time = meeting_duration * sample_duration_fraction
            segments.append(
                MeetingSegment(meeting_id=meeting_id, utterance_cutoff_time=cutoff_time)
            )

        return segments

    logger.info("Selecting first %d meetings", num_meetings)
    return [
        MeetingSegment(meeting_id=meeting_id, utterance_cutoff_time=None)
        for meeting_id in meeting_ids[:num_meetings]
    ]
