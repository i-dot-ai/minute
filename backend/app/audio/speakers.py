import logging

from backend.app.audio.speaker_recognition import generate_speaker_predictions as predict_speakers
from backend.app.minutes.types import DialogueEntry

logger = logging.getLogger(__name__)


def convert_input_dialogue_entries_to_dialogue_entries(
    entries: list[dict],
) -> list[DialogueEntry]:
    """
    Convert input dialogue entries to DialogueEntry objects.

    Args:
        entries: List of dictionary entries with speaker, text, offsetMilliseconds, and durationMilliseconds

    Returns:
        List of DialogueEntry objects
    """
    return [
        DialogueEntry(
            speaker=entry["speaker"],
            text=entry["text"],
            start_time=float(entry["offsetMilliseconds"]) / 1000,
            end_time=(float(entry["offsetMilliseconds"]) + float(entry["durationMilliseconds"])) / 1000,
        )
        for entry in entries
    ]


def group_dialogue_entries_by_speaker(
    entries: list[DialogueEntry],
) -> list[DialogueEntry]:
    """
    Group consecutive dialogue entries by the same speaker.

    Args:
        entries: List of DialogueEntry objects

    Returns:
        List of DialogueEntry objects with consecutive entries by the same speaker merged
    """
    grouped_entries: list[DialogueEntry] = []
    current_speaker = None
    current_entry = None

    for entry in entries:
        if entry["speaker"] != current_speaker:
            if current_entry:
                grouped_entries.append(current_entry)
            current_speaker = entry["speaker"]
            current_entry = DialogueEntry(
                speaker=current_speaker,
                text=entry["text"],
                start_time=entry["start_time"],
                end_time=entry["end_time"],
            )
        elif current_entry:
            current_entry["text"] += f" {entry['text']}"
            current_entry["end_time"] = entry["end_time"]

    if current_entry:
        grouped_entries.append(current_entry)

    return grouped_entries


def normalize_speaker_labels(entries: list[DialogueEntry]) -> list[DialogueEntry]:
    """
    Normalize speaker labels to sequential numbers starting from 0.

    Args:
        entries: List of DialogueEntry objects

    Returns:
        List of DialogueEntry objects with normalized speaker labels
    """
    speaker_map: dict[str, str] = {}
    current_speaker_index = 0

    normalized_entries = []
    for entry in entries:
        if entry["speaker"] not in speaker_map:
            speaker_map[entry["speaker"]] = str(current_speaker_index)
            current_speaker_index += 1

        normalized_entries.append(
            DialogueEntry(
                speaker=speaker_map[entry["speaker"]],
                text=entry["text"],
                start_time=entry["start_time"],
                end_time=entry["end_time"],
            )
        )

    return normalized_entries


def add_speaker_labels_to_dialogue_entries(
    entries: list[DialogueEntry],
) -> list[DialogueEntry]:
    """
    Add 'Unknown speaker' prefix to speaker labels.

    Args:
        entries: List of DialogueEntry objects

    Returns:
        List of DialogueEntry objects with 'Unknown speaker' prefix added to speaker labels
    """
    return [
        DialogueEntry(
            speaker=f"Unknown speaker {entry['speaker']}",
            text=entry["text"],
            start_time=entry["start_time"],
            end_time=entry["end_time"],
        )
        for entry in entries
    ]


async def process_speakers_and_dialogue_entries(
    dialogue_entries: list[dict] | list[DialogueEntry],
) -> list[DialogueEntry]:
    """
    Process dialogue entries by grouping, normalizing, labeling, and predicting speakers.

    Args:
        dialogue_entries: List of DialogueEntry objects or dictionaries

    Returns:
        List of DialogueEntry objects with processed speaker labels
    """
    # Convert dictionaries to DialogueEntry objects if needed
    entries_as_objects = []
    for entry in dialogue_entries:
        if isinstance(entry, dict):
            entries_as_objects.append(
                DialogueEntry(
                    speaker=entry.get("speaker", ""),
                    text=entry.get("text", ""),
                    start_time=entry.get("start_time", 0.0),
                    end_time=entry.get("end_time", 0.0),
                )
            )
        else:
            entries_as_objects.append(entry)

    # Step 1: Group similar speakers together
    grouped_dialogue_entries = group_dialogue_entries_by_speaker(entries_as_objects)

    # Step 2: Normalize speaker labels to numbers
    normalised_dialogue_entries = normalize_speaker_labels(grouped_dialogue_entries)

    # Step 3: Add "Unknown speaker" prefix
    labelled_dialogue_entries = add_speaker_labels_to_dialogue_entries(normalised_dialogue_entries)

    try:
        # Step 4: Get speaker predictions
        speaker_predictions = await predict_speakers(labelled_dialogue_entries)

        # Step 5: Update entries with predicted names
        predicted_entries = []
        for entry in labelled_dialogue_entries:
            predicted_entries.append(
                DialogueEntry(
                    speaker=speaker_predictions.get(entry["speaker"], entry["speaker"]),
                    text=entry["text"],
                    start_time=entry["start_time"],
                    end_time=entry["end_time"],
                )
            )

        return predicted_entries
    except Exception as e:  # noqa: BLE001 # flagged by ruff - investigate when we have time.
        logger.error("Error predicting speaker names: %s", str(e))
        # Return the labeled entries if prediction fails
        return labelled_dialogue_entries


# Alias for backward compatibility
process_dialogue_entries = process_speakers_and_dialogue_entries
