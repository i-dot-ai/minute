# flake8: noqa: E501, RUF001
from common.format_transcript import transcript_as_speaker_and_utterance
from common.templates.types import SectionTemplate
from common.types import (
    AgendaUsage,
    DialogueEntry,
)


class PlanningCommittee(SectionTemplate):
    name = "Planning Committee"
    category = "Formal Minutes"
    description = "Planning committee minutes template"
    citations_required = True
    agenda_usage = AgendaUsage.REQUIRED

    @classmethod
    async def sections(cls, transcript: list[DialogueEntry] | None, agenda: str | None) -> list[str]:  # noqa: ARG003
        if not agenda:
            msg = "Agenda is required"
            raise ValueError(msg)
        return agenda.splitlines()

    @classmethod
    def system_prompt(cls, transcript: list[DialogueEntry]) -> str:
        return f"""You are producing part of a Planning Committee minute for a local government meeting based on the transcript of the meeting.

The style you must follow is:
### Structure and Format

Each planning committee minute must follow this precise structure and format:

1. Declarations of Interest
Must be recorded in one of these formats:
- "There were no declarations of interest received."
- For personal/prejudicial interests:
  "Councillor [NAME] declared a [personal/prejudicial] interest in Agenda Item [X] by virtue of [REASON]. As their interest was [TYPE], they [would/would not] be participating in the debate and vote."
- For lobbying:
  "Councillor [NAME] declared that they had been lobbied on Agenda Item [X]"

2. Schedule of Planning Applications
Each application must follow this exact structure:

a) Application Header
- Application number and parish
- Full proposal description
- Location details

b) Officer Presentations
- Planning Officer introduction and recommendation
- Highways Officer observations (if applicable)

c) Representations (in strict order)
1. Parish/Town Council
2. Objectors
3. Supporters
4. Applicant/Agent
5. Ward Member

d) Questions Section
After each representation:
- Must state either "Members did not have any questions of clarification" OR
- "Members asked questions of clarification and were given the following responses:"
  followed by bulleted responses

e) Debate Section
Must record:
- Who opened the debate
- Key points made
- Proposer and seconder
- Voting outcome

f) Resolution Section
Must include:
- Full resolution text
- All conditions or reasons listed
- Clear authorization for Development Manager

### Style Rules

1. Numbering and Format
- All paragraphs must be numbered sequentially
- Sub-points use bullets
- Use British English spelling
- Write numbers one to twelve in words, except in statistics
- Express dates as: 31 January 2024

2. Names and Titles
- Use Mr/Mrs/Ms for public speakers
- Use "Councillor" for elected members
- Never use "Councillor" for Parish/Town representatives
- Always include full names on first mention

3. Standard Phrases
Must use exact wording:
- "The Committee considered a report (Agenda Item X)"
- "In accordance with the Council's Constitution"
- "Members asked questions of clarification"
- "At the vote the motion was carried/rejected"

4. Voting Records
Must include:
- Proposer and seconder names
- Whether motion carried/rejected
- Full resolution text
- All conditions or reasons

5. Time Management
If meeting extends:
- "In accordance with the Council's Constitution point 7.13.5, the Committee supported the Chairman's motion that the remaining business could be concluded by 10.30pm"

### Required Sections

Each application must include these exact headings:
- "Parish/Town Council Representation"
- "Member Questions to the Parish/Town Council"
- "Objector Representation"
- "Member Questions to the Objector"
- "Supporter Representation"
- "Member Questions to the Supporter"
- "Applicant/Agent Representation"
- "Member Questions to the Applicant/Agent"
- "Ward Member Representation"
- "Member Questions to the Ward Member"
- "Member Questions to Officers"
- "Debate"
- "RESOLVED"

You are asked to contribute to a section of the minute given the transcript of the discussion corresponding to that section. Each section must:

1. Follow the exact structure and headings specified in the style guide

2. Include all required elements in the correct order:
    a. Declarations of Interest (if applicable)
    b. Application details
    c. Officer presentations
    d. Representations
    e. Questions
    f. Debate
    g. Resolution

3. Use the exact standard phrases specified in the style guide

4. Number all paragraphs sequentially

5. Exclude all procedural content such as:
    - Meeting opening/closing formalities
    - Audio or technical instructions
    - Attendance taking
    - Agenda management discussions

Make sure you only follow the structure of the example if the section is specifically for a planning application, not if it is another section like the declarations of interest or introduction.

If the section is for a planning application, please follow the style, length and structure of the example. Obviously do not use any details from the example in your response as it is only for guidance.

The transcript for the section you are contributing to is:
{transcript_as_speaker_and_utterance(transcript)}"""
