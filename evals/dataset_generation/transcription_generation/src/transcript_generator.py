import logging

from common.database.postgres_models import DialogueEntry
from common.llm.client import ChatBot, FastOrBestLLM, create_default_chatbot
from evals.dataset_generation.transcription_generation.src.config import PromptConfig, TranscriptGenerationConfig

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
            speaker_ids[0]: [{"role": "system", "content": self._create_system_prompt(actor_definitions[1])}],
            speaker_ids[1]: [{"role": "system", "content": self._create_system_prompt(actor_definitions[0])}],
        }

        transcript: list[DialogueEntry] = []
        current_message = ""
        word_count = 0

        while word_count < self.generation_config.max_words:
            logger.info("Word count: %d/%d", word_count, self.generation_config.max_words)

            histories[speaker_ids[0]].append({"role": "user", "content": current_message})
            histories[speaker_ids[0]] = self._trim_history(histories[speaker_ids[0]])
            reply_1 = await self.chatbot.chat(histories[speaker_ids[0]])
            word_count += len(reply_1.split())
            transcript.append(
                DialogueEntry(
                    speaker="1",
                    text=reply_1,
                    start_time=0.0,  # Placeholder for audio generation
                    end_time=0.0,  # Placeholder for audio generation
                )
            )
            histories[speaker_ids[0]].append({"role": "assistant", "content": reply_1})

            histories[speaker_ids[1]].append({"role": "user", "content": reply_1})
            histories[speaker_ids[1]] = self._trim_history(histories[speaker_ids[1]])
            reply_2 = await self.chatbot.chat(histories[speaker_ids[1]])
            word_count += len(reply_2.split())
            transcript.append(
                DialogueEntry(
                    speaker="2",
                    text=reply_2,
                    start_time=0.0,  # Placeholder for audio generation
                    end_time=0.0,  # Placeholder for audio generation
                )
            )
            histories[speaker_ids[1]].append({"role": "assistant", "content": reply_2})

            current_message = reply_2

        logger.info("Generated transcript with %d entries and %d words", len(transcript), word_count)
        return transcript
