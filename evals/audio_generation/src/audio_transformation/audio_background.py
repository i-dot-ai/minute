import io
import logging
from pathlib import Path

from pydub import AudioSegment

from evals.audio_generation.src.settings import AUDIO_GEN_DIR, BACKGROUND_VOLUME_OFFSET, OUTPUT_DIR
from evals.audio_generation.src.utils.parsing_utils import make_timestamp

logger = logging.getLogger(__name__)


def mix_audio_with_background(speech_audio: bytes, effects_audio: bytes, speech_name: str, sfx_name: str) -> Path:
    """
    Overlays two audio files saving the return the file. Returns the output's file path
    """
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    dialogue = AudioSegment.from_mp3(io.BytesIO(speech_audio))
    background = AudioSegment.from_mp3(io.BytesIO(effects_audio))

    background = background + BACKGROUND_VOLUME_OFFSET

    if len(background) < len(dialogue):
        loops_needed = (len(dialogue) // len(background)) + 1
        background = (background * loops_needed)[: len(dialogue)]
    else:
        background = background[: len(dialogue)]

    final: AudioSegment = dialogue.overlay(background)

    output_path = output_dir / f"{speech_name}_mixed_{sfx_name}_{make_timestamp()}.mp3"
    final.export(output_path, format="mp3")

    logger.info("Mixed audio saved to %s", output_path)

    return output_path


def mp3_to_bytes(mp3_path: str | Path) -> tuple[str, bytes]:
    """
    Reads an MP3 file and returns its name and content as bytes.
    mp3_path may be derived from either the input or output dir
    """
    audio_gen_root = AUDIO_GEN_DIR
    path = (audio_gen_root / mp3_path).resolve()

    if not path.exists():
        msg = f"MP3 file not found: {path}"
        raise FileNotFoundError(msg)

    file_name = path.stem

    return file_name.split("_", 1)[0], path.read_bytes()
