import logging
from functools import cached_property

from common.llm.client import ChatBot
from evals.dataset_generation.transcription_generation.src.constants import (
    FACILITATOR_REMINDER_TEMPLATE,
    FACILITATOR_TEMPLATE,
    get_template,
)
from evals.dataset_generation.transcription_generation.src.history_manager import HistoryManager
from evals.dataset_generation.transcription_generation.src.models import FacilitatorDecision
from evals.dataset_generation.transcription_generation.src.participant import Participant

logger = logging.getLogger(__name__)


class Facilitator(Participant):
    def __init__(
        self,
        history_manager: HistoryManager,
        actor_definitions: list[str],
        speaker_ids: list[str],
        identifier: str = "facilitator",
        chatbot: ChatBot | None = None,
    ) -> None:
        super().__init__(identifier, history_manager, chatbot)
        self.actor_definitions = actor_definitions
        self.speaker_ids = set(speaker_ids)

    @property
    def system_message_content(self) -> str:
        return self._static_system_prompt

    @cached_property
    def _static_system_prompt(self) -> str:
        template = get_template(FACILITATOR_TEMPLATE)
        roles = list(zip(sorted(self.speaker_ids), self.actor_definitions, strict=False))
        return template.render(
            roles=roles,
            conversation_history=None,
            speakers_who_havent_spoken=None,
        )

    def _build_facilitator_messages(self) -> list[dict]:
        messages = [{"role": "system", "content": self._static_system_prompt}]

        for entry in self.history_manager.history:
            messages.append({"role": "user", "content": f"Speaker {entry.speaker_id} said: {entry.content}"})

        spoken_speakers = {speaker_id for speaker_id, _ in self.history_manager.history}
        unspoken_speakers = self.speaker_ids - spoken_speakers

        if unspoken_speakers:
            reminder_template = get_template(FACILITATOR_REMINDER_TEMPLATE)
            reminder = reminder_template.render(speakers_who_havent_spoken=unspoken_speakers)
            messages.append({"role": "user", "content": reminder})

        messages.append(
            {"role": "user", "content": "Based on the conversation above, decide which speaker should speak next."}
        )

        return messages

    async def decide_next_speaker(self) -> tuple[str, bool]:
        messages = self._build_facilitator_messages()
        response = await self.chatbot.structured_chat(messages, response_format=FacilitatorDecision)

        next_speaker = response.next_speaker_id
        should_terminate = response.should_terminate
        logger.info("Facilitator selected next speaker: %s, should_terminate: %s", next_speaker, should_terminate)
        return next_speaker, should_terminate
