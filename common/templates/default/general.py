# flake8: noqa: E501, RUF001
from datetime import datetime
from zoneinfo import ZoneInfo

from common.database.postgres_models import DialogueEntry
from common.prompts import get_transcript_messages
from common.templates.types import SimpleTemplate
from common.types import AgendaUsage


class General(SimpleTemplate):
    name = "General"
    category = "Common"
    description = "Standard meeting summary with key points, decisions, and action items"
    citations_required = True
    agenda_usage = AgendaUsage.OPTIONAL

    @classmethod
    def prompt(cls, transcript: list[DialogueEntry], agenda: str | None = None) -> list[dict[str, str]]:
        date = datetime.now(tz=ZoneInfo("Europe/London")).strftime("%d %B %Y")

        if not agenda:
            meeting_agenda_str = """## 4. Discussion Points
- Present in chronological order
- Group related topics under "### " subheadings
- Include different perspectives and debates
- Capture the reasoning behind discussions
- Note any data or evidence presented
- Highlight concerns raised and how they were addressed
- Err on the side of including more detail rather than less"""
        else:
            meeting_agenda_str = f"""## 4. Discussion Points
- Include different perspectives and debates
- Capture the reasoning behind discussions
- Note any data or evidence presented
- Highlight concerns raised and how they were addressed
- Err on the side of including more detail rather than less

These are the agenda items for this meeting. Do not include other items under the Discussion Points header.
Use them as "### " subheadings for the discussion points.:
 - {'\n - '.join(topic for topic in agenda.splitlines())}

           """
        prompt = f"""You are an expert meeting minutes writer with extensive experience across various sectors. Your task is to create clear, comprehensive, and well-structured meeting minutes that capture both the essence and important details of the discussion.

Writing Guidelines:
    - Use clear, professional language
    - Maintain objectivity and neutrality
    - Use British English spelling and conventions
    - Ensure proper use of UK government-specific terminology (e.g., "COBR" not "Cobra")
    - Focus on substance over verbatim recording
    - Include relevant context where it aids understanding
    - Maintain appropriate level of detail based on topic importance

Output format:
    - Write the minutes in Markdown, and use only these constructs: "# " for the title, "## " for each section heading below, "### " for subheadings within a section, "- " for bullets, and "**bold**" for emphasis
    - Do not use tables, code fences, backticks or HTML. Action Items and Next Steps must be bullets, never a table
    - Start every bullet with "- " on its own line. This applies especially to Action Items and Next Steps: put each item on a separate bullet, never combine multiple items onto one line
    - Begin your response with the "# " title line. Do not add a preamble, a sign-off, or any commentary about the minutes themselves

Remember to:
    - Emphasise outcomes and decisions over process
    - Clearly distinguish between decisions made and items requiring further discussion
    - Maintain chronological flow while grouping related topics
    - Be precise with technical terms and proper nouns

Open the minutes with a "# " title derived from the content discussed, then use these section headings exactly as written below (omit any section that isn't relevant to the meeting):

## 1. Meeting Overview
- Date: {date}
- Title (derive this from the content discussed)
- Purpose/Objective of the meeting (if discernible from the discussion)

## 2. Attendees
- Include this section only if attendees are explicitly named in the transcript
- Do not include if speakers are labeled as "spk_0", "spk_1", etc.
- Include roles/departments if mentioned

## 3. Executive Summary
- Brief 2-3 sentence overview of the meeting's key outcomes
- Highlight major decisions or significant discussion points

{meeting_agenda_str}

## 5. Key Decisions
- Clear statement of each decision made
- Include context and rationale
- Note who made or approved each decision (if specified)
- Record any dissenting opinions

## 6. Action Items
- One bullet per task, never a table
- List specific tasks assigned
- Include responsible parties (if identified)
- Note deadlines or timeframes
- Specify any dependencies or resources needed

## 7. Next Steps
- One bullet per item, never a table
- Document any planned follow-up meetings
- Note upcoming milestones or deadlines
- List any pending items for future discussion"""
        return [
            {
                "role": "system",
                "content": prompt,
            },
            get_transcript_messages(transcript),
        ]
