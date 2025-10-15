import re

from common.database.postgres_models import DialogueEntry
from common.llm.client import FastOrBestLLM, create_default_chatbot
from common.prompts import get_citations_prompt


async def add_citations_to_minute(
    transcript: list[DialogueEntry],
    initial_draft: str,
) -> str:
    chatbot = create_default_chatbot(FastOrBestLLM.FAST)
    messages = get_citations_prompt(initial_draft, transcript)

    minute = await chatbot.chat(messages)

    minute = combine_consecutive_citations(minute)

    return minute or ""


MAX_CITATION_DISTANCE = 2

cluster_pattern = re.compile(r"(\[\d+\])+")
citation_pattern = re.compile(r"\d+")


def combine_consecutive_citations(minute: str) -> str:
    matches = cluster_pattern.finditer(minute)
    for match in matches:
        citation_cluster = match.group()
        numbers = [int(n.group()) for n in citation_pattern.finditer(citation_cluster)]
        numbers.sort()
        # Extract individual numbers from the cluster
        groups = []
        for number in numbers:
            if len(groups) == 0 or abs(groups[-1][-1] - number) > MAX_CITATION_DISTANCE:
                groups.append([number])
            else:
                groups[-1].append(number)

        out = ""
        for citation_group in groups:
            if len(citation_group) == 1:
                out += f"[{citation_group[0]}]"
            else:
                out += f"[{citation_group[0]}-{citation_group[-1]}]"
        minute = minute.replace(citation_cluster, out)
    return minute
