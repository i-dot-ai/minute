import asyncio
import logging

from common.llm.client import FastOrBestLLM, create_default_chatbot
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Set up the environment with the templates directory
template_dir = Path(__file__).parent.parent / "prompts"
env = Environment(loader=FileSystemLoader(template_dir))


async def main(SYSTEM_PROMPT_1, SYSTEM_PROMPT_2) -> None:


    # Load a specific template
    template = env.get_template("actor_system.j2")

    # Render with context
    system_prompt_actor_one = template.render(role_definition=SYSTEM_PROMPT_1)

    # Render with context
    system_prompt_actor_two = template.render(role_definition=SYSTEM_PROMPT_2)


    # temp Config
    NUM_TURNS = 3
    MAX_WORDS= 400 #assuming 1500 words every 10mins 
    SPEAKERS = ["speaker_1", "speaker_2"]

    # temp Prompts
    # SYSTEM_PROMPT_1 = "You are a upbeat female doctor with three grandchildren interviewing a patient, offering advice, diagnostics and general health and well being advice."
    # SYSTEM_PROMPT_2 = "You are a middle aged melancholic middle aged man looking for a diagnosis, advice and general health and well being advice from a doctor. You are open and honest about your symptoms and lifestyle."
    INITIAL_MESSAGE = ""

    # histories and transcript
    histories = {
        "speaker_1": [{"role": "system", "content": system_prompt_actor_two}],
        "speaker_2": [{"role": "system", "content":system_prompt_actor_one }],
    }
    # transcript = [{"speaker": "2", "text": INITIAL_MESSAGE}]

    transcript = []


    chatbot = create_default_chatbot(FastOrBestLLM.FAST)


    current_message = INITIAL_MESSAGE
    WORD_COUNT = 0
    
    while MAX_WORDS is None or WORD_COUNT < MAX_WORDS:
        logger.info("Word Count: %s", WORD_COUNT)

        # speaker 1 responds
        histories["speaker_1"].append({"role": "user", "content": current_message})
        reply1 = await chatbot.chat(histories["speaker_1"])
        WORD_COUNT += len(reply1.split(" "))
        transcript.append({"speaker": "1", "text": reply1})
        histories["speaker_1"].append({"role": "assistant", "content": reply1})

        # speaker 2 responds
        histories["speaker_2"].append({"role": "user", "content": reply1})
        reply2 = await chatbot.chat(histories["speaker_2"])
        WORD_COUNT += len(reply2.split(" "))
        transcript.append({"speaker": "2", "text": reply2})
        histories["speaker_2"].append({"role": "assistant", "content": reply2})

        current_message = reply2



    logger.info("Transcript: \n %s", transcript)
