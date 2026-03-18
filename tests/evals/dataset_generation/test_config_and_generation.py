from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from evals.dataset_generation.transcription_generation.src.config import TranscriptGenerationConfig
from evals.dataset_generation.transcription_generation.src.transcript_generator import (
    NoticeType,
    TranscriptGenerator,
)


@pytest.fixture
def basic_config():
    return TranscriptGenerationConfig(
        theme="Medical consultation",
        word_target=100,
        num_speakers=2,
    )


@pytest.fixture
def mock_actor_definitions():
    return ["Doctor in a medical consultation", "Patient seeking medical advice"]


def test_transcript_generation_config_default_values():
    config = TranscriptGenerationConfig(theme="Test theme")

    assert config.theme == "Test theme"
    assert config.word_target == 400
    assert config.termination_threshold_multiplier == 1.25
    assert config.num_speakers == 2


def test_transcript_generation_config_speaker_ids_property():
    config = TranscriptGenerationConfig(theme="Test", num_speakers=3)

    assert config.speaker_ids == ["speaker_1", "speaker_2", "speaker_3"]


def test_transcript_generation_config_theme_required():
    with pytest.raises(ValidationError):
        TranscriptGenerationConfig()


def test_classify_notice_type():
    config = TranscriptGenerationConfig(theme="Test", word_target=100)
    generator = TranscriptGenerator(generation_config=config)

    assert generator._classify_notice_type(50) == NoticeType.NONE  # noqa: SLF001
    assert generator._classify_notice_type(92) == NoticeType.SOFT  # noqa: SLF001
    assert generator._classify_notice_type(99) == NoticeType.HARD  # noqa: SLF001


@pytest.mark.asyncio
async def test_generate_transcript_raises_on_mismatched_actor_count(basic_config):
    generator = TranscriptGenerator(generation_config=basic_config)

    with pytest.raises(ValueError, match="Expected 2 actors, got 1"):
        await generator.generate_transcript(["Only one actor"])


@pytest.mark.asyncio
async def test_generate_transcript_returns_dialogue_entries(basic_config, mock_actor_definitions):
    from unittest.mock import AsyncMock

    with (
        patch("evals.dataset_generation.transcription_generation.src.transcript_generator.Actor") as mock_actor_class,
        patch(
            "evals.dataset_generation.transcription_generation.src.transcript_generator.Facilitator"
        ) as mock_facilitator_class,
        patch("evals.dataset_generation.transcription_generation.src.transcript_generator.create_default_chatbot"),
        patch(
            "evals.dataset_generation.transcription_generation.src.transcript_generator.HistoryManager"
        ) as mock_history_class,
    ):
        mock_history = Mock()
        mock_history.history = [
            Mock(speaker_id="init_user_message", content="Let's begin"),
            Mock(speaker_id="speaker_1", content="Hello"),
        ]
        mock_history_class.return_value = mock_history

        mock_actor_instance = AsyncMock()
        mock_actor_instance.reply_to_last_message = AsyncMock(return_value="Test response")
        mock_actor_class.return_value = mock_actor_instance

        mock_facilitator_instance = AsyncMock()
        mock_facilitator_instance.decide_next_speaker = AsyncMock(return_value=("speaker_1", True))
        mock_facilitator_instance.history_manager = mock_history
        mock_facilitator_class.return_value = mock_facilitator_instance

        generator = TranscriptGenerator(generation_config=basic_config)
        result = await generator.generate_transcript(mock_actor_definitions)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(entry, dict) for entry in result)
        assert all("speaker" in entry and "text" in entry for entry in result)
        assert all(entry["speaker"] != "init_user_message" for entry in result)
