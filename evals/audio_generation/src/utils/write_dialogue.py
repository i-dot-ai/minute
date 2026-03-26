import json
from pathlib import Path

from evals.audio_generation.src.utils.dialogue import DialogueEntry


def write_dialogue(entries: list[DialogueEntry], output_path: Path) -> None:
    """
    Writes the provided dialogue to file matching the data contract
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {
            "speaker": e.speaker,
            "text": e.text,
            "start_time": e.start_time,
            "end_time": e.end_time,
        }
        for e in entries
    ]

    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
