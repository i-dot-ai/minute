import argparse
import json
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from evals.audio_generation.src.settings import AUDIO_GEN_DIR, INPUT_DIR
from evals.audio_generation.src.utils.dialogue import DialogueEntry


class AudioArgs(Namespace):
    mode: str | None


def save_audio(
    full_audio: bytes,
    output_file: str | Path,
    target_dir: Path | None = None,
) -> str:
    """
    Saves audio bytes to a file as mp3.

    By default, saves to `audio_generation/output` directory.
    The caller can override this by passing `target_dir`.

    Returns the absolute path to the saved file as a string.
    """

    if target_dir is None:
        target_dir = AUDIO_GEN_DIR / "output"
    else:
        target_dir = Path(target_dir)

        if not target_dir.is_absolute():
            target_dir = AUDIO_GEN_DIR / target_dir

    target_dir.mkdir(parents=True, exist_ok=True)

    full_output_path = target_dir / output_file
    if full_output_path.suffix != ".mp3":
        full_output_path = full_output_path.with_suffix(".mp3")

    full_output_path = full_output_path.with_stem(f"{full_output_path.stem}_{make_timestamp()}")

    full_output_path.write_bytes(full_audio)
    return str(full_output_path.relative_to(AUDIO_GEN_DIR))


def make_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def get_transcripts(file_name: str) -> list[DialogueEntry]:
    """
    Returns transcript data as a list of DialogueEntry objects.
    """
    transcript_file = INPUT_DIR / "transcripts" / file_name

    if not transcript_file.is_file():
        error_message = f"Transcript file not found: {transcript_file}"
        raise FileNotFoundError(error_message)

    data = json.loads(transcript_file.read_text(encoding="utf-8"))

    return [
        DialogueEntry(
            speaker=entry["speaker"],
            text=entry["text"].strip(),
            start_time=float(entry["start_time"]),
            end_time=float(entry["end_time"]),
        )
        for entry in data
    ]


def parse_args() -> AudioArgs:
    parser = argparse.ArgumentParser(description="Audio generation CLI")

    parser.add_argument(
        "mode",
        nargs="?",
        default=None,
        choices=[None, "with-background-sfx"],
        help="Optional: add 'with-background-sfx' to mix audio",
    )

    args = parser.parse_args(namespace=AudioArgs())

    return cast(AudioArgs, args)
