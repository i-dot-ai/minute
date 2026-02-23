from __future__ import annotations

from evals.transcription.src.core.segments import (
    convert_to_diarization_format,
    format_segments_with_speakers,
)


def test_convert_to_diarization_format_with_dicts():
    segments = [
        {"speaker": "A", "text": "hello", "start": 0.0, "end": 1.0},
        {"speaker": "B", "text": "world", "start": 1.0, "end": 2.0},
    ]
    result = convert_to_diarization_format(segments)
    assert result == [
        {"speaker": "A", "text": "hello", "start": 0.0, "end": 1.0},
        {"speaker": "B", "text": "world", "start": 1.0, "end": 2.0},
    ]


def test_convert_to_diarization_format_with_start_time_end_time():
    segments = [
        {"speaker": "A", "text": "hello", "start_time": 0.5, "end_time": 1.5},
    ]
    result = convert_to_diarization_format(segments)
    assert result == [
        {"speaker": "A", "text": "hello", "start": 0.5, "end": 1.5},
    ]


def test_convert_to_diarization_format_with_objects():
    class Segment:
        def __init__(self, speaker, text, start, end):
            self.speaker = speaker
            self.text = text
            self.start = start
            self.end = end

    segments = [
        Segment("A", "hello", 0.0, 1.0),
        Segment("B", "world", 1.0, 2.0),
    ]
    result = convert_to_diarization_format(segments)
    assert result == [
        {"speaker": "A", "text": "hello", "start": 0.0, "end": 1.0},
        {"speaker": "B", "text": "world", "start": 1.0, "end": 2.0},
    ]


def test_convert_to_diarization_format_with_start_time_attribute():
    class Segment:
        def __init__(self, speaker, text, start_time, end_time):
            self.speaker = speaker
            self.text = text
            self.start_time = start_time
            self.end_time = end_time

    segments = [Segment("A", "hello", 0.5, 1.5)]
    result = convert_to_diarization_format(segments)
    assert result == [
        {"speaker": "A", "text": "hello", "start": 0.5, "end": 1.5},
    ]


def test_convert_to_diarization_format_empty():
    result = convert_to_diarization_format([])
    assert result == []


def test_format_segments_with_speakers_basic():
    segments = [
        {"speaker": "A", "text": "Hello world"},
        {"speaker": "B", "text": "Good morning"},
    ]
    result = format_segments_with_speakers(segments)
    assert result == "[A] hello world [B] good morning"


def test_format_segments_with_speakers_empty():
    result = format_segments_with_speakers([])
    assert result == ""


def test_format_segments_with_speakers_with_empty_text():
    segments = [
        {"speaker": "A", "text": "Hello"},
        {"speaker": "B", "text": "   "},
        {"speaker": "C", "text": "World"},
    ]
    result = format_segments_with_speakers(segments)
    assert result == "[A] hello [C] world"


def test_format_segments_with_speakers_with_reference():
    ref_segments = [
        {"speaker": "Speaker_1", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_2", "text": "good morning", "start": 1.0, "end": 2.0},
    ]
    hyp_segments = [
        {"speaker": "Speaker_A", "text": "hello world", "start": 0.0, "end": 1.0},
        {"speaker": "Speaker_B", "text": "good morning", "start": 1.0, "end": 2.0},
    ]
    result = format_segments_with_speakers(hyp_segments, ref_segments)
    assert "[Speaker_1]" in result or "[Speaker_A]" in result
    assert "hello world" in result
    assert "good morning" in result


def test_format_segments_with_speakers_normalizes_text():
    segments = [
        {"speaker": "A", "text": "Hello, World!"},
        {"speaker": "B", "text": "GOOD MORNING"},
    ]
    result = format_segments_with_speakers(segments)
    assert result == "[A] hello world [B] good morning"


def test_format_segments_with_speakers_removes_punctuation():
    segments = [
        {"speaker": "A", "text": "Hello... world!!!"},
    ]
    result = format_segments_with_speakers(segments)
    assert result == "[A] hello world"
