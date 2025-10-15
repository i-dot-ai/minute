# flake8: noqa: E501, RUF001,
from pydantic import BaseModel, Field

from common.format_transcript import transcript_as_speaker_and_utterance
from common.llm.client import FastOrBestLLM, create_default_chatbot
from common.prompts import get_sections_from_transcript_prompt
from common.templates.types import SectionTemplate
from common.types import (
    AgendaUsage,
    DialogueEntry,
)


class MeetingSections(BaseModel):
    sections_list: list[str] = Field(
        description="A list of distinct discussion topics or agenda items covered during a formal meeting, such as 'Opening Remarks', 'Previous Actions Review', 'Main Discussion Points', 'Action Items', or 'Closing Summary'. Must be in the order they appear in the transcript."
    )


style_guide_for_record_of_discussion = """### Style
The Cabinet minute is written in past reported speech. In other words, it reports what people said, not what they did, or how they spoke. A few important style rules flow from this:

- First, stage directions are plain and kept to an absolute minimum. The standard introduction to any speaker is: SPEAKER_NAME said that […..]. The minute always uses “said that” and never “explained”, “noted”, “commented” or other variants. Things like small talk, welcoming attendees, etc. should be omitted even if that means items like the introduction and conclusion are quite short.

- Second, the minute is written in the perfect tense, and always in the third person.  This means:
    - every verb goes back one step further into the past. For future verbs, these become conditional (i.e. “I will” becomes “(s)he would”);
    - “I/we” become “(s)he/they”. Sometimes “we” may also become “the Government”, if this adds to the clarity of the minute;
    - References to times or dates must be written so that it is clear to when a speaker was referring when the record is read in 20 years’ time.  This means the minute uses either “that”, “the previous” or “the following”. Therefore:
    - References to current time periods, such as “today”, “this week”, “this year”, become “that day”, “that week”, “that year”, and so on;
    - References to past time periods, such as “yesterday” or “last week” become “the previous day”, “the previous week”, and so on;
    - References to future time periods, such as “tomorrow”, “next week” become “the following day”, “the following year”, and so on.
    - Usually it is not necessary to specify individual days of the week. Therefore “later that week” or “the following week” tend to suffice.
    - When using reported speech it is grammatically correct to use either simply “(s)he said” or  “(s)he said that”. The Cabinet convention is the latter. Please do include the “that”.

The examples below set out how these rules work in practice, on some common points that arise during Cabinet meetings:
    - “I announced the proposals today” becomes “[(S)He said that] (s)he had announced the proposals that day”.
    - “The changes will be implemented next year” becomes “The changes would be implemented the following year”.
    - “The figures were published today” becomes “The figures had been published that day”.
    - “I spoke to the President yesterday” becomes “He had spoken to President [Name] the previous day”.
    - “We will be going to the summit on Saturday” becomes “they would be going to/attending the summit later that week”
    - “I expect that the French will block agreement” becomes “He expected that the French would block the agreement”; or “It was likely that the French would block the agreement”.
    - “We must argue strongly against the Commission proposals” becomes “The UK/the Government must argue strongly against the Commission proposals”.  [Note:  sometimes, on Foreign Affairs items, putting “the UK” into the third person every time becomes too cumbersome.  The occasional - exceptional - “we” is OK.]


### Grammar, punctuation, spelling and capitals

The Cabinet Minute maintains strict rules on grammar, including some which are specific to its drafting. This section sets out some common inaccuracies, as well as specific rules for drafting the Minute. In particular:
- British English spelling *must* be used. For example, "colour" not "color" and "emphasise" not "emphasize".
- Split infinitives should not be included.
- Lack of hyphens. Government documents have a tendency to be hyphen-free. However, the Cabinet Minute insists on hyphens in compound adjectives appearing before a noun, particularly where the meaning is otherwise not clear. For example: “in the long term”, but “a long-term trend”; “lone parents”, but “lone-parent families”; “fixed-term parliaments”.
- Sentences without verbs, or two sentences joined together only with commas. “The Summit would discuss overseas aid, there would be a dinner on the final evening” needs either a full-stop in the middle or the word “and”;
- Sentences should not end with prepositions. For example “The Government needed to consider which areas it should intervene on” becomes “The Government needed to consider on which areas it should intervene” or even better “The Government should consider where and how to intervene”.

There are a number of other rules specific to the Cabinet Minute, even if this conflicts with other Government style guides:
- There should be no contractions. “Was not” “it is” and “did not” rather than “wasn’t” “it’s” and hadn’t”;
- “Per cent” is written out in words, never “%”;
- Spending is expressed: “£2 billion” (not “£2billion”, “£2 bn” or “£2bn”);
- Financial years use hyphens not slashes, i.e “2012-13” not “2012/13”;
- Dates are expressed: 31 January, 1 March, 2 June;
- Use the words for numbers one to twelve (subject to the bullet below), but figures for numbers higher.  E.g. “Twelve people had been killed in the blast, and 40 had been injured”;
- Having said this, percentages or statistics always use figures. E.g.  “GDP had risen by 1 per cent”;
- If you have to express a half, follow the same convention as above.  So:  “The grant scheme had been in place for four-and-a-half years and had increased employment by 5.5 per cent during this time”.

There are also a number of conventions for capitalisation:
- Government has a capital letter only when it is preceded by “the”.
- Use ALL CAPS for speaker names and minister titles. You must always use the title of a minister over their name. Never include both together in the minute.
- Departments and civil servants are not capitalised unless using a proper noun. E.g. the Department for Work and Pensions or the Civil Service.
- Local government, local authorities and councils are not capitalised.
- Fiscal events are always capitalised, but not associated timeframes e.g. “the Spending Review” but “the summer Budget”.
- Stages of Parliamentary proceedings should also be capitalised, e.g. “Second Reading”, “Report” (but not “stage” in Report stage).
- Specific bills should be capitalised, but not when the term is used generically. So “the Housing Bill” but “there would be “20 bills”. It should also be “Private Members’ Bills”.
- Other EU countries are always Member States.
- When discussing the courts, there is no capital, but the Supreme Court is always capitalised.
- “The economy” is not capitalised.
- Similarly, neither are “devolved administrations” (though it would still be the “Scottish/Welsh/Northern Ireland Government” as above)
- “Parliament” should be capitalised, but “parliamentary” should not be.

In addition, there are various other oddities on which conventions have evolved over the course of time for writing the Minute:

- Proper nouns can be abbreviated after the first mention, so long as the abbreviation is included afterwards in parentheses. For example: The Department for the Environment, Food and Rural Affairs (DEFRA) can subsequently be called DEFRA.  Similarly, the House of Commons should be written out in full the first time but thereafter simply “the House”; the House of Lords subsequently “the Lords”;
- The Minute avoids acronyms for two-word titles – for example the Environment Agency or for unusual technical terms that are unlikely to appear in the Cabinet Minute again in the near future;
- Very, very common abbreviations in the UK (e.g. UK, EU, UN, NHS) do not need to be spelt out in full;
- When the Minute refers to the current Government, say “the Government” (note: not “this” Government).  Other Governments will require a qualifier to explain who you mean, eg the previous Government, the last Conservative Government, the French Government, rogue Governments etc;
- Similarly, foreign ministers should generally have their country prefaced to their title. For instance: Russian President Putin;
- Never abbreviate people’s names - for example Aung Sang Suu Kyi not ASSK;
- IED remains as IED;
- Islamic State was referred to as ISIL until December 2015, whereafter “Daesh” has been used.  “Daesh” should be used until otherwise stated.


There are a number of ministerial titles that differ from common usage for the purpose of attributing the Minute. These should always be in block capitals. When another Cabinet member refers to them, this can be minuted as spoken.

- Chancellor – The Chancellor of the Exchequer;
- Secretary of State for Justice – The Lord Chancellor and Secretary of State for Justice;
- Home Secretary – The Secretary of State for the Home Department;
- Foreign Secretary – The Secretary of State for Foreign and Commonwealth Affairs;
- Chief Whip – The Chief Whip and Parliamentary Secretary to the Treasury;

In addition, there are a number of ministerial titles that vary with the office holder:

- If a minister is made First Secretary of State, this should be minuted the first time a point is attributed and thereafter they should just be referred to by their ministerial title. For example: “The First Secretary of State and Chancellor of the Exchequer” thereafter “The Chancellor of the Exchequer”’
- If a minister is appointed “Chancellor of the Duchy of Lancaster” this is how they are referred to in the minute;

Junior Ministers should normally be referred to using their full title on Gov.uk, for example: The Minister of State for Universities, Science, Research and Innovation rather than The Minister of State at the Department of Business for Education and the Department for Business, Energy and Industrial Strategy. This is partly because there may be two officeholders with the same title in the latter format, and it should be clear from the cover page of the minute who you are referring to.

You must always use the title of a minister over their name if both are provided."""

example_item = r"""THE SECRETARY OF STATE FOR [  ] said that she had announced proposals for the regulation of the industry the previous day. These had been received well, though there had been some criticism of the ban on [  ] because of its impact on small businesses.  Her Department would be publishing detailed guidance later that year.

Continuing,  THE SECRETARY OF STATE FOR [  ] said that….

Concluding, THE SECRETARY OF STATE FOR [  ] said that….

THE DEPUTY PRIME MINISTER said that he was grateful to the Secretary of State for [  ]  and her officials for their work on the package. This illustrated that the Coalition was fulfilling its promise to support those who [  ]. Separate discussions would be needed to agree the detailed guidance, following the consultation.

In discussion the following points were made:

a.	  the package was excellent, and would support growth by [  ];

b.	 [….];

Responding, THE SECRETARY OF STATE FOR [  ] said that….

Summing up, THE PRIME MINISTER said that…"""


class Cabinet(SectionTemplate):
    name = "Cabinet"
    category = "Formal Minutes"
    description = "Formal minutes following cabinet meeting structure"
    citations_required = True
    agenda_usage = AgendaUsage.OPTIONAL

    @classmethod
    def system_prompt(
        cls,
        transcript: list[DialogueEntry],
    ) -> str:
        return rf"""You are producing part of a Cabinet Style minute for a UK government meeting based on the transcript of the meeting.

The style you must follow is:
{style_guide_for_record_of_discussion}

You are asked to contribute to an item of the minute given the transcript of the discussion corresponding to that item. Each item must:

1. Begin directly with substantive content - never start with procedural phrases like "SPEAKER said the next item was..." or any meeting logistics/audio instructions

2. Follow this structure for substantial items:
    a. Main content introduction from the Chair:
        - First paragraph: "SPEAKER_NAME said that..." (focusing on the actual topic)
        - Additional paragraphs if needed: "Continuing, SPEAKER_NAME said that..."
        - Final paragraph (if 3+ paragraphs): "Concluding, SPEAKER_NAME said that..."
        - Keep paragraphs to roughly half a page maximum

    b. Record contributions from key speakers (Prime Minister, relevant Secretary of State, etc.)

    c. Discussion points:
        - Begin with "In discussion, the following points were made:"
        - Use bullet points with semicolons
        - Order chronologically or by theme
        - Include disagreements without minimizing them
        - Don't duplicate identical points
        - Omit simple questions, but include their answers

    d. Responses:
        - Begin with "Responding, SPEAKER_NAME said that..."
        - Include answers to points raised

    e. Summary (if applicable):
        - Record thanks to colleagues/departments
        - Note resolved differences
        - List actions

3. For brief items or introductions/conclusions, a simpler structure may be used

4. Include a section heading with two hashes (##)

5. Exclude all procedural content such as:
    - Meeting opening/closing formalities
    - Audio or technical instructions
    - Attendance taking
    - Agenda announcements
    - Speaking procedure reminders

The transcript for the item you are contributing to is:
{transcript_as_speaker_and_utterance(transcript)}"""

    @classmethod
    async def sections(cls, transcript: list[DialogueEntry] | None, agenda: str | None) -> list[str]:
        if not agenda:
            chatbot = create_default_chatbot(FastOrBestLLM.FAST)
            messages = get_sections_from_transcript_prompt(transcript=transcript)
            response = await chatbot.structured_chat(
                messages=messages,
                response_format=MeetingSections,
            )
            return response.sections_list
        else:
            return agenda.splitlines()
