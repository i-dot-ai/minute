from pathlib import Path

from evals.audio_generation.src.audio_transformation.audio_background import mix_audio_with_background, mp3_to_bytes
from evals.audio_generation.src.settings import INPUT_DIR, OUTPUT_DIR


def audio_with_background_fx(
    transcript_file: str | Path,
    sfx_file: str | Path,
) -> None:
    """
    Workflow combines stored audio dialogue and sound-effect files
    into a single mixed audio track. Pass arguments relative
    to the output & input dirs
    """
    transcript_audio_file = Path(transcript_file)
    sfx_file = Path(sfx_file)

    speech_name, audio_bytes = mp3_to_bytes(OUTPUT_DIR / transcript_audio_file)
    sfx_name, sfx_bytes = mp3_to_bytes(INPUT_DIR / sfx_file)
    mix_audio_with_background(audio_bytes, sfx_bytes, speech_name, sfx_name)
