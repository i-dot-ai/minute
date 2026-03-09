import asyncio
import logging
from pydantic import BaseModel
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from common.llm.client import FastOrBestLLM, create_default_chatbot
from evals.dataset_generation.transcription_generation.src.generate_transcript import main

logger = logging.getLogger(__name__)

class ActorsResponse(BaseModel):
    actors_definitions: list[str]

# Set up the environment with the templates directory
template_dir = Path(__file__).parent.parent / "prompts"
env = Environment(loader=FileSystemLoader(template_dir))
theme = "Doctor patient consultation about fatigue"

# Load a specific template
template = env.get_template("actor_generator.j2")
 
# Render with context
output = template.render(theme=theme)

chatbot = create_default_chatbot(FastOrBestLLM.FAST)
async def generate_prompt() -> None:

    reply = await chatbot.structured_chat([{"role": "system", "content": output}], response_format=ActorsResponse)
    # print(reply.actors_definitions[0])    
    # print(reply.actors_definitions[1])
    await main(SYSTEM_PROMPT_1=reply.actors_definitions[0], SYSTEM_PROMPT_2=reply.actors_definitions[1])


asyncio.run(generate_prompt())

