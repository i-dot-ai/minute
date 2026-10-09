# flake8: noqa: E501
"""Action: apply user-provided AI edit instructions to an existing minute version."""

from common.database.postgres_models import DialogueEntry
from common.settings import get_structured_logger
from worker.llm import FastOrBestLLM, create_default_chatbot
from worker.text import transcript_as_speaker_and_utterance

slogger = get_structured_logger()


def _edit_messages(minutes: str, edit_instructions: str, transcript: list[DialogueEntry]) -> list[dict[str, str]]:
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
        {
            "role": "user",
            "content": f"Here is the meeting transcript:\n{transcript_as_speaker_and_utterance(transcript)}",
        },
        {"role": "user", "content": "Here is the summary of the meeting for which you will edit:" + minutes},
        {
            "role": "user",
            "content": "Here are the instructions the user provided for editing the summary:" + edit_instructions,
        },
    ]


async def edit_minutes(minutes: str, edit_instructions: str, transcript: list[DialogueEntry]) -> str:
    slogger.info(
        "Applying AI edit to minutes: {num_chars} chars, instructions: {num_instruction_chars} chars",
        num_chars=len(minutes),
        num_instruction_chars=len(edit_instructions),
    )
    chatbot = create_default_chatbot(FastOrBestLLM.FAST)
    edited_minutes = await chatbot.chat(messages=_edit_messages(minutes, edit_instructions, transcript))
    return edited_minutes.removeprefix("```html").removesuffix("```")
