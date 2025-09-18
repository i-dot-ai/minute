from common.database.postgres_models import DialogueEntry


def transcript_as_speaker_and_utterance(transcript: list[DialogueEntry]) -> str:
    return "\n".join([f"{item['speaker']}: {item['text']}" for item in transcript])


def transcript_as_index_speaker_and_utterance(transcript: list[DialogueEntry]) -> str:
    return "\n".join(f"[{i}] {entry['speaker']}: {entry['text']}" for i, entry in enumerate(transcript))
