import logging

from common.format_transcript import transcript_as_speaker_and_utterance
from common.llm.client import create_default_chatbot
from common.types import DialogueEntry, SpeakerPredictionOutput

logger = logging.getLogger(__name__)


async def generate_speaker_predictions(dialogue_entries: list[DialogueEntry]) -> dict[str, str]:
    """
    Generate speaker name predictions based on dialogue entries.

    Args:
        dialogue_entries: List of DialogueEntry objects containing speaker and text

    Returns:
        Dictionary mapping original speaker labels to predicted names
    """
    # Create a system message that explains the task
    system_message = """You are an expert at analysing conversation transcripts and identifying speakers.
Based on the conversation content, identify the names of the speakers.
Only make high-confidence identifications, otherwise keep the original speaker label. Pay careful attention to whether the speaker is saying their own name or referring to another speaker.
Do not use any names that are not in the transcript.
For each speaker, provide:
- The original speaker label
- Your identified name (this will be the original speaker label if you are not confident)"""  # noqa: E501

    # Create the user message
    user_message = f"""Please analyse this conversation and suggest real names for speakers currently labeled as 'Speaker 1', 'Speaker 2', etc. Only suggest changes if you're confident.

Conversation:
{transcript_as_speaker_and_utterance(dialogue_entries)}
    """  # noqa: E501

    try:
        chatbot = create_default_chatbot()
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

        speaker_prediction = await chatbot.structured_chat(messages, response_format=SpeakerPredictionOutput)

        if not speaker_prediction.predictions:
            logger.warning("No predictions found, returning original speaker labels")
            return {entry["speaker"]: entry["speaker"] for entry in dialogue_entries}

        return {pred.original_speaker: pred.predicted_name for pred in speaker_prediction.predictions}
    except Exception as e:  # noqa: BLE001 # flagged by ruff - investigate when we have time.
        error_message = str(e)
        # Check for content filter errors from Azure OpenAI
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
            # Log the content filter error but continue with original speaker labels
            logger.warning(
                "Content filter detected in transcript. Continuing with original speaker labels: %s", error_message
            )

            # Return original speaker labels
            return {entry["speaker"]: entry["speaker"] for entry in dialogue_entries}
        else:
            # For other errors, log and return original speaker labels
            logger.error("Error predicting speaker names: %s", error_message)
            return {entry["speaker"]: entry["speaker"] for entry in dialogue_entries}
