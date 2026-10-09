"""Action: predict real speaker names for a transcript, falling back to generic labels on failure."""

from common.settings import get_structured_logger
from common.types import DialogueEntry, SpeakerPredictionOutput
from worker.llm import FastOrBestLLM, create_default_chatbot
from worker.text import transcript_as_speaker_and_utterance

slogger = get_structured_logger()


def group_dialogue_entries_by_speaker(entries: list[DialogueEntry]) -> list[DialogueEntry]:
    """Merge consecutive dialogue entries by the same speaker."""
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
    """Normalize speaker labels to sequential numbers starting from 1."""
    speaker_map: dict[str, str] = {}
    current_speaker_index = 1

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


def add_speaker_labels_to_dialogue_entries(entries: list[DialogueEntry]) -> list[DialogueEntry]:
    """Add 'Speaker' prefix to speaker labels."""
    return [
        DialogueEntry(
            speaker=f"Speaker {entry['speaker']}",
            text=entry["text"],
            start_time=entry["start_time"],
            end_time=entry["end_time"],
        )
        for entry in entries
    ]


async def _generate_speaker_predictions(dialogue_entries: list[DialogueEntry]) -> dict[str, str]:
    """Generate speaker name predictions based on dialogue entries."""
    system_message = """You are an expert at analysing conversation transcripts and identifying speakers.
Based on the conversation content, identify the names of the speakers.
Only make high-confidence identifications, otherwise keep the original speaker label. Pay careful attention to whether the speaker is saying their own name or referring to another speaker.
Do not use any names that are not in the transcript.
For each speaker, provide:
- The original speaker label
- Your identified name (this will be the original speaker label if you are not confident)"""  # noqa: E501

    user_message = f"""Please analyse this conversation and suggest real names for speakers currently labeled as 'Speaker 1', 'Speaker 2', etc. Only suggest changes if you're confident.

Conversation:
{transcript_as_speaker_and_utterance(dialogue_entries)}
    """  # noqa: E501

    try:
        chatbot = create_default_chatbot(FastOrBestLLM.FAST)
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

        speaker_prediction = await chatbot.structured_chat(messages, response_format=SpeakerPredictionOutput)

        if not speaker_prediction.predictions:
            slogger.warning("No speaker predictions found, keeping original speaker labels")
            return {entry["speaker"]: entry["speaker"] for entry in dialogue_entries}

        return {pred.original_speaker: pred.predicted_name for pred in speaker_prediction.predictions}
    except Exception as e:  # noqa: BLE001 # flagged by ruff - investigate when we have time.
        error_message = str(e)
        # Check for content filter errors from the LLM provider
        if any(
            term in error_message.lower()
            for term in [
                "content_filter",
                "content filter",
                "content management policy",
                "filtered",
                "policy violation",
            ]
        ):
            slogger.warning(
                "Content filter detected in transcript, keeping original speaker labels: {error}",
                error=error_message,
            )
            return {entry["speaker"]: entry["speaker"] for entry in dialogue_entries}
        slogger.error("Speaker prediction failed, keeping original speaker labels: {error}", error=error_message)
        return {entry["speaker"]: entry["speaker"] for entry in dialogue_entries}


async def identify_speakers(dialogue_entries: list[DialogueEntry]) -> list[DialogueEntry]:
    """Process dialogue entries by grouping, normalizing, labeling, and predicting speakers."""
    grouped_dialogue_entries = group_dialogue_entries_by_speaker(dialogue_entries)
    normalised_dialogue_entries = normalize_speaker_labels(grouped_dialogue_entries)
    labelled_dialogue_entries = add_speaker_labels_to_dialogue_entries(normalised_dialogue_entries)

    try:
        speaker_predictions = await _generate_speaker_predictions(labelled_dialogue_entries)
        predicted_entries = [
            DialogueEntry(
                speaker=speaker_predictions.get(entry["speaker"], entry["speaker"]),
                text=entry["text"],
                start_time=entry["start_time"],
                end_time=entry["end_time"],
            )
            for entry in labelled_dialogue_entries
        ]
        slogger.info(
            "Speaker identification completed: {num_entries} entries, {num_speakers} speakers",
            num_entries=len(predicted_entries),
            num_speakers=len({entry["speaker"] for entry in predicted_entries}),
        )
        return predicted_entries
    except Exception:
        slogger.exception("Speaker processing failed, using labelled entries")
        return labelled_dialogue_entries
