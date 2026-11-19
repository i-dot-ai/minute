# flake8: noqa: E501, RUF001
from common.database.postgres_models import DialogueEntry
from common.prompts import get_transcript_messages
from common.templates.types import SimpleTemplate
from common.types import AgendaUsage


class ExecutiveSummary(SimpleTemplate):
    name = "Short 'n' Sweet"
    category = "Common"
    description = "Executive summary of the meeting + action items"
    citations_required = False
    agenda_usage = AgendaUsage.NOT_USED

    @classmethod
    def prompt(cls, transcript: list[DialogueEntry], agenda: str | None = None) -> list[dict[str, str]]:  # noqa: ARG003
        prompt = """You are an expert meeting summary writer. You are given a transcript of a meeting and you need to generate a concise summary of the meeting. The user has been told that this is a 'short and sweet' summary, so ensure that the summary is relatively short.

Your summary should:
- Be concise, clear and to the point, focusing on the most important information
- Include a section for action items, clearly listing tasks assigned, responsible parties (if mentioned), and any deadlines
- Use British English spelling and conventions
- Do not hallucinate, only include information that is explicitly mentioned in the transcript

Format the action items as a bulleted list for clarity."""
        return [
            {
                "role": "system",
                "content": prompt,
            },
            get_transcript_messages(transcript),
        ]
