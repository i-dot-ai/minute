import logging

from common.database.postgres_models import DialogueEntry
from common.llm.client import ChatBot, FastOrBestLLM, create_default_chatbot
from evals.dataset_generation.transcription_generation.src.config import PromptConfig, TranscriptGenerationConfig
from evals.dataset_generation.transcription_generation.src.facilitator import Facilitator

logger = logging.getLogger(__name__)


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

    def _trim_history(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        if self.generation_config.max_words_per_turn is None:
            return history

        system_messages = [msg for msg in history if msg["role"] == "system"]
        conversation_messages = [msg for msg in history if msg["role"] != "system"]

        total_words = sum(len(msg["content"].split()) for msg in conversation_messages)

        while total_words > self.generation_config.max_words_per_turn and len(conversation_messages) > 1:
            removed_msg = conversation_messages.pop(0)
            total_words -= len(removed_msg["content"].split())

        return system_messages + conversation_messages

    async def generate_transcript(self, actor_definitions: list[str]) -> list[DialogueEntry]:
        if len(actor_definitions) != self.generation_config.num_speakers:
            msg = f"Expected {self.generation_config.num_speakers} actors, got {len(actor_definitions)}"
            raise ValueError(msg)

        speaker_ids = self.generation_config.speaker_ids
        histories: dict[str, list[dict[str, str]]] = {
            speaker_id: [{"role": "system", "content": self._create_system_prompt(actor_def)}]
            for speaker_id, actor_def in zip(speaker_ids, actor_definitions, strict=False)
        }

        facilitator = Facilitator(
            actor_definitions=actor_definitions, speaker_ids=speaker_ids, prompt_config=self.prompt_config
        )

        transcript: list[DialogueEntry] = []
        word_count = 0
        last_message = ""

        current_speaker_id = speaker_ids[0]

        while word_count < self.generation_config.max_words:
            logger.info("Word count: %d/%d", word_count, self.generation_config.max_words)

            histories[current_speaker_id].append({"role": "user", "content": last_message})
            histories[current_speaker_id] = self._trim_history(histories[current_speaker_id])

            reply = await self.chatbot.chat(histories[current_speaker_id])
            word_count += len(reply.split())

            speaker_number = speaker_ids.index(current_speaker_id) + 1
            transcript.append(
                DialogueEntry(
                    speaker=str(speaker_number),
                    text=reply,
                    start_time=0.0,  # Placeholder for audio generation
                    end_time=0.0,  # Placeholder for audio generation
                )
            )

            histories[current_speaker_id].append({"role": "assistant", "content": reply})
            facilitator.add_to_history(current_speaker_id, reply)

            last_message = reply

            if word_count < self.generation_config.max_words:
                current_speaker_id = await facilitator.decide_next_speaker()

        logger.info("Generated transcript with %d entries and %d words", len(transcript), word_count)
        return transcript
