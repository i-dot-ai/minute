import json

from evals.audio_generation.src.utils.parsing_utils import get_transcripts


def test_get_transcripts(tmp_path):
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()

    file = transcripts_dir / "test_transcript.json"

    mock_json = [
        {
            "speaker": "Alice",
            "text": " Hello ",
            "start_time": 0.0,
            "end_time": 1.0,
        }
    ]

    file.write_text(json.dumps(mock_json))

    from evals.audio_generation.src.utils import parsing_utils

    parsing_utils.INPUT_DIR = tmp_path

    result = get_transcripts("test_transcript.json")

    assert len(result) == 1
    assert result[0].speaker == "Alice"
    assert result[0].text == "Hello"
    assert result[0].start_time == 0.0
    assert result[0].end_time == 1.0
