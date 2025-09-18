import logging

from common.audio.generate_speaker_predictions import generate_speaker_predictions
from common.types import DialogueEntry

logger = logging.getLogger(__name__)


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
    dialogue_entries: list[DialogueEntry],
) -> list[DialogueEntry]:
    """
    Process dialogue entries by grouping, normalizing, labeling, and predicting speakers.

    Args:
        dialogue_entries: List of DialogueEntry objects or dictionaries

    Returns:
        List of DialogueEntry objects with processed speaker labels
    """

    # Step 1: Group similar speakers together
    grouped_dialogue_entries = group_dialogue_entries_by_speaker(dialogue_entries)

    # Step 2: Normalize speaker labels to numbers
    normalised_dialogue_entries = normalize_speaker_labels(grouped_dialogue_entries)

    # Step 3: Add "Unknown speaker" prefix
    labelled_dialogue_entries = add_speaker_labels_to_dialogue_entries(normalised_dialogue_entries)

    try:
        # Step 4: Get speaker predictions
        speaker_predictions = await generate_speaker_predictions(labelled_dialogue_entries)

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
