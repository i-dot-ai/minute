from common.database.postgres_models import DialogueEntry
from common.llm.client import FastOrBestLLM, create_default_chatbot
from common.prompts import get_citations_prompt


async def add_citations_to_minute(
    transcript: list[DialogueEntry],
    initial_draft: str,
) -> str:
    chatbot = create_default_chatbot(FastOrBestLLM.FAST)
    messages = get_citations_prompt(initial_draft, transcript)

    choice = await chatbot.chat(messages)

    return choice or ""
