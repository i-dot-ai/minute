# flake8: noqa: E501

from common.database.postgres_models import DialogueEntry
from common.format_transcript import transcript_as_index_speaker_and_utterance, transcript_as_speaker_and_utterance


def get_transcript_messages(transcript: list[DialogueEntry]) -> dict[str, str]:
    return {
        "role": "user",
        "content": f"Here is the meeting transcript:\n{transcript_as_speaker_and_utterance(transcript)}",
    }


def get_minutes_messages(minutes: str) -> dict[str, str]:
    return {"role": "user", "content": "Here is the summary of the meeting for which you will edit:" + minutes}


def get_ai_edit_initial_messages(
    minutes: str, edit_instructions: str, transcript: list[DialogueEntry]
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": "You are a meeting minutes editor. You are given a transcript of a meeting and a summary of that meeting. "
            "You are also given instructions for editing the summary. "
            "You should edit the summary according to the instructions. "
            "Do not return anything other than the edited summary. "
            "Your output should be in HTML format and must not contain any code fences or other formatting. "
            "Do not reformat anything in square brackets, but keep them in their original style, for example [1][2][3] should remain as [1][2][3] rather than be [1-3]",
        },
        get_transcript_messages(transcript),
        get_minutes_messages(minutes),
        {
            "role": "user",
            "content": "Here are the instructions the user provided for editing the summary:" + edit_instructions,
        },
    ]


def get_chat_with_transcript_system_message(transcript: list[DialogueEntry]) -> dict[str, str]:
    return {
        "role": "system",
        "content": f"""You are given a transcript of a meeting. Your role is to respond to the user's requests about the transcript.
Your answers should only use the information contained in the transcript. Do not reference anything outside of the transcript.
You should add citations where necessary. Each citation should be of the form [n] where n is the index of the transcript item. Each citation should be one number surrounded by square brackets. For example, you must do [80][81] not [80, 81]
Here is the meeting transcript:\n{transcript_as_index_speaker_and_utterance(transcript)}""",
    }


def get_basic_minutes_prompt(
    transcript: list[DialogueEntry],
) -> list[dict[str, str]]:
    """
    A function to generate a basic meeting minutes prompt based on a provided transcript of dialogues. It combines
    a generic prompt with the transcript entries to create a structured message list. Intended to be used
    as a fall back when no other summary type is suitable, due to the likelihood of hallucinations.
    """
    prompt = """Provide a simple summary of the meeting."""
    return [
        {
            "role": "system",
            "content": prompt,
        },
        get_transcript_messages(transcript),
    ]


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


def get_meeting_detection_prompt(transcript: list[DialogueEntry]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": "Your task is to identify if the transcript appears to be a long meeting between "
            "multiple parties, involving a substantial amount of discussion between multiple speakers."
            " Return True if the transcript appears to be a long meeting, and False if it appears to be a short meeting.",
        },
        get_transcript_messages(transcript),
    ]


def get_hallucination_detection_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "user",
            "content": """Is your above output consistent with the instructions you were given, or is there evidence of hallucination?""",
        }
    ]


def format_guidelines(guidelines: str | list[str]) -> str:
    """Format guidelines as markdown bullet points.

    Args:
        guidelines: Either a pre-formatted string or a list of guideline strings

    Returns:
        A string with guidelines formatted as markdown bullet points
    """
    if isinstance(guidelines, list):
        return "\n".join(f"- {guideline}" for guideline in guidelines)
    return guidelines


def get_section_for_agenda_prompt(section: str) -> dict[str, str]:
    return {"role": "user", "content": f"The item of the meeting that you will be contributing to is: {section}"}


async def get_citations_prompt(initial_draft: str, transcript: list[DialogueEntry]):
    return [
        {
            "role": "system",
            "content": """You are tasked with adding citations to a minutes document produced from the transcript of a meeting.

Here is some guidance you must follow:
Your goal is to add citations to the minutes document without changing the minutes document itself.
Only return the minutes document with citations added. Do not return anything else.
You will only change the minutes document if there are parts of it that are not coherent with each other, or if there is duplication.
You must also ensure all spelling is British English, not American English.
Government acronyms must be spelt correctly even if spelt incorrectly in the transcript. For example: "COBR" not "COBRA".
Each citation should be of the form [n] where n is the index of the transcript item. Each citation should be one number surrounded by square brackets. For example, you must do [80][81] not [80, 81]
""",
        },
        {
            "role": "user",
            "content": f"""Here is the meeting transcript:
{transcript_as_index_speaker_and_utterance(transcript)}

And here is the minutes document which you will add citations to:
{initial_draft}""",
        },
    ]


def string_to_system_message(string: str) -> dict[str, str]:
    return {"role": "system", "content": string}
