import logging

from common.llm.client import ChatBot, FastOrBestLLM, create_default_chatbot
from evals.dataset_generation.transcription_generation.src.constants import FACILITATOR_TEMPLATE, get_template
from evals.dataset_generation.transcription_generation.src.models import FacilitatorDecision

logger = logging.getLogger(__name__)


class Facilitator:
    def __init__(
        self,
        actor_definitions: list[str],
        speaker_ids: list[str],
        chatbot: ChatBot | None = None,
    ) -> None:
        self.actor_definitions = actor_definitions
        self.speaker_ids = speaker_ids
        self.chatbot = chatbot or create_default_chatbot(FastOrBestLLM.FAST)
        self.conversation_history: list[tuple[str, str]] = []

    def _create_facilitator_prompt(self) -> str:
        template = get_template(FACILITATOR_TEMPLATE)
        roles = list(zip(self.speaker_ids, self.actor_definitions, strict=False))
        speakers_who_spoke = {speaker_id for speaker_id, _ in self.conversation_history}
        speakers_who_havent_spoken = [sid for sid in self.speaker_ids if sid not in speakers_who_spoke]
        return template.render(
            roles=roles,
            conversation_history=self.conversation_history,
            speakers_who_havent_spoken=speakers_who_havent_spoken,
        )

    async def decide_next_speaker(self) -> tuple[str, bool]:
        prompt = self._create_facilitator_prompt()

        response = await self.chatbot.structured_chat(
            [{"role": "system", "content": prompt}], response_format=FacilitatorDecision
        )

        next_speaker = response.next_speaker_id
        should_terminate = response.should_terminate
        logger.info("Facilitator selected next speaker: %s, should_terminate: %s", next_speaker, should_terminate)
        return next_speaker, should_terminate

    def add_to_history(self, speaker_id: str, text: str) -> None:
        self.conversation_history.append((speaker_id, text))
