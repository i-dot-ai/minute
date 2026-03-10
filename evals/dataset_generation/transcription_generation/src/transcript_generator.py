import logging
import math

from common.database.postgres_models import DialogueEntry
from common.llm.client import ChatBot, FastOrBestLLM, create_default_chatbot
from evals.dataset_generation.transcription_generation.src.config import PromptConfig, TranscriptGenerationConfig
from evals.dataset_generation.transcription_generation.src.facilitator import Facilitator
from evals.dataset_generation.transcription_generation.src.participant import Actor, ChatEntry

logger = logging.getLogger(__name__)
HARD_CLOSE_THRESHOLD = 2
SOFT_CLOSE_THRESHOLD = 10


class TranscriptGenerator:
    def __init__(
        self,
        chatbot: ChatBot | None = None,
        generation_config: TranscriptGenerationConfig | None = None,
        prompt_config: PromptConfig | None = None,
    ) -> None:
        self.chatbot = chatbot or create_default_chatbot(FastOrBestLLM.FAST)
        self.generation_config = generation_config or TranscriptGenerationConfig(theme="Default conversation theme")
        self.prompt_config = prompt_config or PromptConfig()
        self.env = self.prompt_config.create_environment()

    def _create_system_prompt(self, actor_definition: str) -> str:
        template = self.env.get_template(self.prompt_config.actor_system_template)
        return template.render(role_definition=actor_definition)

    def _create_time_remaining_message(self, current_word_count: int) -> str:
        template = self.env.get_template(self.prompt_config.time_remaining_template)
        words_remaining = max(0, self.generation_config.word_target - current_word_count)
        minutes_remaining_perc = math.ceil(words_remaining / self.generation_config.word_target * 100)  # rename
        hard_close = minutes_remaining_perc < HARD_CLOSE_THRESHOLD  # need to make configurable
        soft_close = minutes_remaining_perc < SOFT_CLOSE_THRESHOLD
        return template.render(
            minutes_remaining_perc=minutes_remaining_perc, hard_close=hard_close, soft_close=soft_close
        )

    def _trim_history(self, history: list[ChatEntry]) -> list[ChatEntry]:
        if self.generation_config.max_words_per_turn is None:
            return history

        system_messages = [msg for msg in history if msg.role == "system"]
        conversation_messages = [msg for msg in history if msg.role != "system"]

        total_words = sum(len(msg.content.split()) for msg in conversation_messages)

        while total_words > self.generation_config.max_words_per_turn and len(conversation_messages) > 1:
            removed_msg = conversation_messages.pop(0)
            total_words -= len(removed_msg.content.split())

        return system_messages + conversation_messages

    async def generate_transcript(self, actor_definitions: list[str]) -> list[DialogueEntry]:
        if len(actor_definitions) != self.generation_config.num_speakers:
            msg = f"Expected {self.generation_config.num_speakers} actors, got {len(actor_definitions)}"
            raise ValueError(msg)

        speaker_ids = self.generation_config.speaker_ids

        actors: dict[str, Actor] = {}
        for speaker_id, actor_def in zip(speaker_ids, actor_definitions, strict=False):
            actor = Actor(speaker_id)
            actor.add_to_history(ChatEntry(role="system", content=self._create_system_prompt(actor_def)))
            actors[speaker_id] = actor

        facilitator = Facilitator(
            actor_definitions=actor_definitions, speaker_ids=speaker_ids, prompt_config=self.prompt_config
        )

        transcript: list[DialogueEntry] = []
        word_count = 0
        last_message = ""

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

            time_remaining_msg = self._create_time_remaining_message(word_count)
            user_message = f"{time_remaining_msg}\n\n{last_message}" if last_message else time_remaining_msg

            current_actor = actors[current_speaker_id]
            current_actor.add_to_history(ChatEntry(role="user", content=user_message))
            current_actor.history = self._trim_history(current_actor.history)

            reply = await current_actor.reply_to_last_message()
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

            current_actor.add_to_history(ChatEntry(role="assistant", content=reply))
            facilitator.add_to_history(current_speaker_id, reply)

            last_message = reply

            if word_count < hard_termination_threshold:
                current_speaker_id, should_terminate = await facilitator.decide_next_speaker()
                if should_terminate:
                    logger.info("Meeting terminated by facilitator (participants ready to wrap up)")
                    break

        logger.info("Generated transcript with %d entries and %d words", len(transcript), word_count)
        return transcript
