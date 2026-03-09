import asyncio
import logging

from common.llm.client import FastOrBestLLM, create_default_chatbot

logger = logging.getLogger(__name__)

# temp Config
NUM_TURNS = 3
SPEAKERS = ["speaker_1", "speaker_2"]

# temp Prompts
SYSTEM_PROMPT_1 = "You are a doctor interviewing a patient."
SYSTEM_PROMPT_2 = "You are a patient looking for a diagnosis"
INITIAL_MESSAGE = "Hello. Who are you?"

# histories and transcript
histories = {
    "speaker_1": [{"role": "system", "content": SYSTEM_PROMPT_1}],
    "speaker_2": [{"role": "system", "content": SYSTEM_PROMPT_2}],
}
transcript = [{"speaker": "2", "text": INITIAL_MESSAGE}]


chatbot = create_default_chatbot(FastOrBestLLM.FAST)


async def run_conversation() -> None:
    current_message = INITIAL_MESSAGE
    for turn in range(NUM_TURNS):
        logger.info("Turn: %s", turn)

        # speaker 1 responds
        histories["speaker_1"].append({"role": "user", "content": current_message})
        reply1 = await chatbot.chat(histories["speaker_1"])
        transcript.append({"speaker": "1", "text": reply1})
        histories["speaker_1"].append({"role": "assistant", "content": reply1})

        # speaker 2 responds
        histories["speaker_2"].append({"role": "user", "content": reply1})
        reply2 = await chatbot.chat(histories["speaker_2"])
        transcript.append({"speaker": "2", "text": reply2})
        histories["speaker_2"].append({"role": "assistant", "content": reply2})

        current_message = reply2


asyncio.run(run_conversation())

logger.info("Transcript: \n %s", transcript)
