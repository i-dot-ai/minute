# flake8: noqa: E501

from common.database.postgres_models import DialogueEntry
from worker.text import transcript_as_index_speaker_and_utterance, transcript_as_speaker_and_utterance


def get_transcript_messages(transcript: list[DialogueEntry]) -> dict[str, str]:
    return {
        "role": "user",
        "content": f"Here is the meeting transcript:\n{transcript_as_speaker_and_utterance(transcript)}",
    }


def get_minutes_messages(minutes: str) -> dict[str, str]:
    return {"role": "user", "content": "Here is the summary of the meeting for which you will edit:" + minutes}


def get_sections_from_transcript_prompt(
    transcript: list[DialogueEntry],
) -> list[dict[str, str]]:
    # Base system message for no agenda
    system_message = """You are an AI meeting assistant. Your task is to take a transcript of a meeting and generate a list of sections that the meeting should be split into.
The sections should be in the order they appear in the transcript. Please think carefully about what the sections should be and based on the content of the transcript. The sections tend to be the high level topics of discussion."""

    return [
        {
            "role": "system",
            "content": system_message,
        },
        get_transcript_messages(transcript),
    ]


def get_section_for_agenda_prompt(section: str) -> dict[str, str]:
    return {"role": "user", "content": f"The item of the meeting that you will be contributing to is: {section}"}


def get_citations_prompt(initial_draft: str, transcript: list[DialogueEntry]):
    return [
        {
            "role": "user",
            "content": f"""<task>
Add citations to the provided meeting summary which reference items in the transcript.
</task>

<transcript>
{transcript_as_index_speaker_and_utterance(transcript)}
</transcript>

<meeting_summary>
{initial_draft}
</meeting_summary>

<formatting_instructions>
Each citation should be of the form [n] where n is the index of the transcript item. Each citation should be one number surrounded by square brackets. For example, you must do [80][81] not [80, 81].
Do not wrap citations in backticks or any other code formatting: write [80], never `[80]`.
</formatting_instructions>

<requirements>
Each statement should have a maximum of 5 citations.
Do not add citations to lists of attendees.
Reproduce the summary's Markdown exactly as given: the same headings, bullets, bold text, tables and line breaks. Adding citations is the only change you may make.
</requirements>

<output>
Output the meeting summary unchanged except for the addition of citations.
Start your response with the first line of the summary. Do not add a preamble, a sign-off, or any commentary about what you have done.
</output>
""",
        }
    ]


def string_to_system_message(string: str) -> dict[str, str]:
    return {"role": "system", "content": string}
