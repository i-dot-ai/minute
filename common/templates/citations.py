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

    minute = strip_preamble(initial_draft, minute or "")
    minute = unwrap_backticked_citations(minute)

    return combine_consecutive_citations(minute)


backticked_citation_pattern = re.compile(r"`{1,2}((?:\[\d+(?:-\d+)?\])+)`{1,2}")


def strip_preamble(initial_draft: str, minute: str) -> str:
    """Drop any commentary the model wrote before the summary itself.

    The citations pass is asked to return the draft unchanged apart from the citations, but it
    sometimes prefaces it with a line such as "Below are the updated meeting minutes". If the draft
    opened with a Markdown heading then nothing can legitimately precede that heading, so anything
    before the first one is the model talking about its own work.
    """
    if not initial_draft.lstrip().startswith("#"):
        return minute
    lines = minute.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("#"):
            return "\n".join(lines[i:])
    return minute


def unwrap_backticked_citations(minute: str) -> str:
    """Remove code formatting from citations, e.g. `[3]` -> [3].

    mistune renders a backticked citation as a <code> element, which the minute editor then shows as
    monospace code rather than as part of the sentence.
    """
    return backticked_citation_pattern.sub(r"\1", minute)


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
