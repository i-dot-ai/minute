import json
from pathlib import Path
from unittest.mock import patch

from evals.audio_generation.src.utils.dialogue import DialogueEntry
from evals.audio_generation.src.utils.write_dialogue import write_dialogue


@patch("evals.audio_generation.src.utils.write_dialogue.Path.write_text")
@patch("evals.audio_generation.src.utils.write_dialogue.Path.mkdir")
def test_write_dialogue(mock_mkdir, mock_write_text):
    entries = [
        DialogueEntry(speaker="Alice", text="Hello", start_time=1.0, end_time=2.0),
        DialogueEntry(speaker="Bob", text="Hi", start_time=3.0, end_time=4.0),
    ]

    output_path = Path("/mock/output/dialogue.json")

    write_dialogue(entries, output_path)

    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_write_text.assert_called_once()

    written_data = mock_write_text.call_args[0][0]

    parsed = json.loads(written_data)

    assert parsed == [
        {
            "speaker": "Alice",
            "text": "Hello",
            "start_time": 1.0,
            "end_time": 2.0,
        },
        {
            "speaker": "Bob",
            "text": "Hi",
            "start_time": 3.0,
            "end_time": 4.0,
        },
    ]
