# ruff: noqa: T201
import json
import sys
from pathlib import Path
from textwrap import fill


def visualize_transcript(transcript_path: Path) -> None:
    with transcript_path.open() as f:
        data = json.load(f)

    print("=" * 80)
    print("TRANSCRIPT VISUALIZATION")
    print("=" * 80)
    print()

    print(f"Theme: {data['theme']}")
    print(f"Word Target: {data['word_target']}")
    print(f"Number of Speakers: {data['num_speakers']}")
    print()

    print("-" * 80)
    print("SPEAKER DEFINITIONS")
    print("-" * 80)
    for i, actor_def in enumerate(data["actor_definitions"], 1):
        role = actor_def.split(" - ")[0] if " - " in actor_def else f"Speaker {i}"
        print(f"\n[Speaker {i}] {role}")
        print(fill(actor_def, width=78, initial_indent="  ", subsequent_indent="  "))
    print()

    print("-" * 80)
    print("DIALOGUE")
    print("-" * 80)
    print()

    speaker_roles = []
    for actor_def in data["actor_definitions"]:
        role = actor_def.split(" - ")[0] if " - " in actor_def else "Unknown"
        speaker_roles.append(role)

    for entry in data["dialogue_entries"]:
        speaker_num = int(entry["speaker"])
        role = speaker_roles[speaker_num - 1] if speaker_num <= len(speaker_roles) else f"Speaker {speaker_num}"

        print(f"[{role}]")
        print(fill(entry["text"], width=78, initial_indent="  ", subsequent_indent="  "))
        print()

    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        transcript_path = Path(sys.argv[1])
    else:
        transcript_path = Path(__file__).parent / "output" / "transcript_20260309_182548.json"

    if not transcript_path.exists():
        print(f"Error: Transcript file not found: {transcript_path}")
        sys.exit(1)

    visualize_transcript(transcript_path)
