from pathlib import Path

from evals.audio_generation.src.settings import OUTPUT_DIR
from evals.audio_generation.src.tts_adapters.base import TTSAdapter
from evals.audio_generation.src.utils.audio_duration import get_audio_duration
from evals.audio_generation.src.utils.dialogue import DialogueEntry
from evals.audio_generation.src.utils.parsing_utils import (
    get_transcripts,
    make_timestamp,
    save_audio,
)
from evals.audio_generation.src.utils.select_voice import get_voice_for_speaker
from evals.audio_generation.src.utils.write_dialogue import write_dialogue


def generate_eleven_tts_audio(
    adapter: TTSAdapter,
    transcript_file: str,
) -> str:
    """
    Full pipeline: transcript → audio file + structured dialogue output
    Returns saved file path
    """

    transcript_data: list[DialogueEntry] = get_transcripts(transcript_file)
    if not transcript_data:
        error_message = "Transcript is empty — nothing to process"
        raise ValueError(error_message)

    transcript_path = Path(transcript_file)

    audio_segments: list[bytes] = []
    dialogue_output: list[DialogueEntry] = []

    current_time = 0.0

    for entry in transcript_data:
        voice_id = get_voice_for_speaker(entry.speaker)

        audio_bytes = adapter.text_to_speech(entry.text, voice_id)

        duration = get_audio_duration(audio_bytes)

        start_time = current_time
        end_time = current_time + duration

        dialogue_output.append(
            DialogueEntry(
                speaker=entry.speaker,
                text=entry.text,
                start_time=start_time,
                end_time=end_time,
            )
        )

        audio_segments.append(audio_bytes)
        current_time = end_time

    full_audio = b"".join(audio_segments)

    timestamp = make_timestamp()

    output_file = f"{transcript_path.stem}_{timestamp}.mp3"
    target_dir = OUTPUT_DIR / "eleven_labs_tts"

    audio_path = save_audio(full_audio, output_file, target_dir=target_dir)

    write_dialogue(dialogue_output, OUTPUT_DIR / "transcripts" / f"{transcript_path.stem}_{timestamp}.json")

    return audio_path
