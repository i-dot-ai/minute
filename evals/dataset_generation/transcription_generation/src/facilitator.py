import logging

from common.llm.client import ChatBot, FastOrBestLLM, create_default_chatbot
from evals.dataset_generation.transcription_generation.src.config import PromptConfig
from evals.dataset_generation.transcription_generation.src.models import FacilitatorDecision

logger = logging.getLogger(__name__)


class Facilitator:
    def __init__(
        self,
        actor_definitions: list[str],
        speaker_ids: list[str],
        chatbot: ChatBot | None = None,
        prompt_config: PromptConfig | None = None,
    ) -> None:
        self.actor_definitions = actor_definitions
        self.speaker_ids = speaker_ids
        self.chatbot = chatbot or create_default_chatbot(FastOrBestLLM.FAST)
        self.prompt_config = prompt_config or PromptConfig()
        self.env = self.prompt_config.create_environment()
        self.conversation_history: list[tuple[str, str]] = []

    def _create_facilitator_prompt(self) -> str:
        template = self.env.get_template(self.prompt_config.facilitator_template)
        roles = list(zip(self.speaker_ids, self.actor_definitions))
        return template.render(roles=roles, conversation_history=self.conversation_history)

    async def decide_next_speaker(self) -> str:
        prompt = self._create_facilitator_prompt()
        
        response = await self.chatbot.structured_chat(
            [{"role": "system", "content": prompt}],
            response_format=FacilitatorDecision
        )
        
        next_speaker = response.next_speaker_id
        logger.info("Facilitator selected next speaker: %s", next_speaker)
        return next_speaker

    def add_to_history(self, speaker_id: str, text: str) -> None:
        self.conversation_history.append((speaker_id, text))
