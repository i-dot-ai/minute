from unittest.mock import AsyncMock, patch

import pytest

from common.audio.speakers import process_speakers_and_dialogue_entries


@pytest.mark.asyncio
async def test_process_speakers_persists_prediction_confidence():
    dialogue_entries = [
        {
            "speaker": "raw-speaker-a",
            "text": "Hello from Alice",
            "start_time": 0.0,
            "end_time": 1.0,
        },
        {
            "speaker": "raw-speaker-a",
            "text": "Continuing",
            "start_time": 1.0,
            "end_time": 2.0,
        },
    ]

    with patch(
        "common.audio.speakers.generate_speaker_predictions",
        new=AsyncMock(
            return_value={
                "Unknown speaker 0": {
                    "predicted_name": "Alice",
                    "confidence": 0.91,
                }
            }
        ),
    ):
        result = await process_speakers_and_dialogue_entries(dialogue_entries)

    assert result == [
        {
            "speaker": "Alice",
            "text": "Hello from Alice Continuing",
            "start_time": 0.0,
            "end_time": 2.0,
            "speaker_confidence": 0.91,
        }
    ]
