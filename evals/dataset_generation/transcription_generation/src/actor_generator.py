import logging

from common.llm.client import ChatBot, FastOrBestLLM, create_default_chatbot
from evals.dataset_generation.transcription_generation.src.constants import ACTOR_GENERATOR_TEMPLATE, get_template
from evals.dataset_generation.transcription_generation.src.models import ActorDefinition

logger = logging.getLogger(__name__)


class ActorGenerator:
    def __init__(self, chatbot: ChatBot | None = None) -> None:
        self.chatbot = chatbot or create_default_chatbot(FastOrBestLLM.BEST)

    async def generate_actor_definitions(self, theme: str, num_speakers: int) -> list[str]:
        template = get_template(ACTOR_GENERATOR_TEMPLATE)
        prompt = template.render(theme=theme, num_speakers=num_speakers)

        response = await self.chatbot.structured_chat(
            [{"role": "system", "content": prompt}], response_format=ActorDefinition
        )

        logger.info("Generated %d actor definitions for theme: %s", len(response.actors_definitions), theme)
        return response.actors_definitions
