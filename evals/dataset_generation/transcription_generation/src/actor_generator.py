import logging

from common.llm.client import ChatBot, FastOrBestLLM, create_default_chatbot
from evals.dataset_generation.transcription_generation.src.config import PromptConfig
from evals.dataset_generation.transcription_generation.src.models import ActorDefinition

logger = logging.getLogger(__name__)


class ActorGenerator:
    def __init__(self, chatbot: ChatBot | None = None, prompt_config: PromptConfig | None = None) -> None:
        self.chatbot = chatbot or create_default_chatbot(FastOrBestLLM.FAST)
        self.prompt_config = prompt_config or PromptConfig()
        self.env = self.prompt_config.create_environment()

    async def generate_actor_definitions(self, theme: str, num_speakers: int) -> list[str]:
        template = self.env.get_template(self.prompt_config.actor_generator_template)
        prompt = template.render(theme=theme, num_speakers=num_speakers)

        response = await self.chatbot.structured_chat(
            [{"role": "system", "content": prompt}], response_format=ActorDefinition
        )

        logger.info("Generated %d actor definitions for theme: %s", len(response.actors_definitions), theme)
        return response.actors_definitions
