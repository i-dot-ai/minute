import logging
import math
from enum import Enum

from common.database.postgres_models import DialogueEntry
from common.llm.client import FastOrBestLLM, create_default_chatbot
from evals.dataset_generation.transcription_generation.src.config import TranscriptGenerationConfig
from evals.dataset_generation.transcription_generation.src.constants import (
    TIME_REMAINING_TEMPLATE,
    get_template,
)
from evals.dataset_generation.transcription_generation.src.facilitator import Facilitator
from evals.dataset_generation.transcription_generation.src.participant import Actor, HistoryManager

logger = logging.getLogger(__name__)
HARD_CLOSE_THRESHOLD = 2
SOFT_CLOSE_THRESHOLD = 10


class NoticeType(Enum):
    NONE = "none"
    SOFT = "soft"
    HARD = "hard"


class TranscriptGenerator:
    def __init__(
        self,
        generation_config: TranscriptGenerationConfig | None = None,
    ) -> None:
        self.generation_config = generation_config or TranscriptGenerationConfig(theme="Default conversation theme")

    def _classify_notice_type(self, current_word_count: int) -> NoticeType:
        words_remaining = max(0, self.generation_config.word_target - current_word_count)
        remaining_perc = math.ceil((words_remaining * 100) / self.generation_config.word_target)
        
        if remaining_perc < HARD_CLOSE_THRESHOLD:
            return NoticeType.HARD
        if remaining_perc < SOFT_CLOSE_THRESHOLD:
            return NoticeType.SOFT
        return NoticeType.NONE
    
    def _get_notice_prompt(self, notice_type: NoticeType) -> str:
        if notice_type == NoticeType.NONE:
            return None
        
        template = get_template(TIME_REMAINING_TEMPLATE)
        return template.render(
            use_hard_ending_notice=(notice_type == NoticeType.HARD),
            use_soft_ending_notice=(notice_type == NoticeType.SOFT)
        )
    
    def _create_time_remaining_message(self, current_word_count: int) -> str | None:
        notice_type = self._classify_notice_type(current_word_count)
        return self._get_notice_prompt(notice_type)


    async def generate_transcript(self, actor_definitions: list[str]) -> list[DialogueEntry]:
        if len(actor_definitions) != self.generation_config.num_speakers:
            msg = f"Expected {self.generation_config.num_speakers} actors, got {len(actor_definitions)}"
            raise ValueError(msg)

        speaker_ids = self.generation_config.speaker_ids

        history_manager = HistoryManager()

        actors: dict[str, Actor] = {}
        for speaker_id, actor_def in zip(speaker_ids, actor_definitions, strict=False):
            actor = Actor(speaker_id, history_manager, actor_def)
            actors[speaker_id] = actor

        facilitator = Facilitator(
            history_manager=HistoryManager(),
            actor_definitions=actor_definitions,
            speaker_ids=speaker_ids,
            identifier="facilitator",
            chatbot=create_default_chatbot(FastOrBestLLM.BEST),
        )

        transcript: list[DialogueEntry] = []
        word_count = 0

        current_speaker_id = speaker_ids[0]
        hard_termination_threshold = int(
            self.generation_config.word_target * self.generation_config.termination_threshold_multiplier
        )

        while word_count < hard_termination_threshold:
            logger.info(
                "Word count: %d/%d (hard limit: %d)",
                word_count,
                self.generation_config.word_target,
                hard_termination_threshold,
            )

            current_actor = actors[current_speaker_id]
            
            notice_message = self._create_time_remaining_message(word_count)
            reply = await current_actor.reply_to_last_message(notice_message)
            word_count += len(reply.split())

            speaker_number = speaker_ids.index(current_speaker_id) + 1
            transcript.append(
                DialogueEntry(
                    speaker=str(speaker_number),
                    text=reply,
                    start_time=0.0,
                    end_time=0.0,
                )
            )

            facilitator.history_manager.add_to_history(reply, current_speaker_id)

            if word_count < hard_termination_threshold:
                current_speaker_id, should_terminate = await facilitator.decide_next_speaker()
                if should_terminate:
                    logger.info("Meeting terminated by facilitator (participants ready to wrap up)")
                    break

        logger.info("Generated transcript with %d entries and %d words", len(transcript), word_count)
        return transcript
