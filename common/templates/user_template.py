import markdownify

from common.database.postgres_models import TemplateType, Transcription, UserTemplate
from common.format_transcript import transcript_as_speaker_and_utterance
from common.llm.client import FastOrBestLLM, create_default_chatbot
from common.prompts import get_transcript_messages
from common.types import LLMHallucination

document_prompt = """<task>
You are an expert meeting minutes writer with extensive experience across various sectors. \
Your task is to create clear, comprehensive, and well-structured meeting minutes that capture \
both the essence and important details of the discussion.

Transform the provided meeting content into structured minutes following the template guidelines precisely.
</task>

<general_information>
  <recording-datetime>{date}</recording-datetime>
</general_information>

<requirements>
- Follow the structure outlined in the <template> section below exactly. \
Do not add additonal sections if they are not specified.
- Include as much detail as possible.
- Follow any style guidelines within the <template> section exactly.
- Use clear, professional language unless otherwise specified.
- Ensure proper use of UK government-specific terminology (e.g., "COBR" not "Cobra").
</requirements>

<template>

{template}

</template>

"""


form_prompt = """
You are helping to fill out a form based on the provided transcript of a meeting. \
Answer the current question based only on information found in the document.

<transcript>
{transcript}
</transcript>

<style_guide>
{style_guide}
</style_guide>

<previously_answered_questions>
{previous_questions}
</previously_answered_questions>

<current_question>
{current_question}
</current_question>

{question_description}
"""

form_system_prompt = """Instructions:
- Answer based solely on information in the transcript
- Follow any specific instructions provided in the question description and style guide
- If the document doesn't contain relevant information, respond with "Information not found in transcript"
- Ensure your answer is consistent with previously answered questions
- Do not repeat information already provided in previous answers unless directly relevant to this question
- You provide only the direct answer to the question. \
Do not include conversational phrases like "Sure!", "Here's the answer:", "Based on the document...", \
or any other preamble. Simply provide the requested information."""


async def generate_user_template(
    template: UserTemplate, transcription: Transcription
) -> tuple[str, list[LLMHallucination]]:
    if template.type == TemplateType.DOCUMENT:
        markdown_template = markdownify.markdownify(template.content, heading_style=markdownify.ATX)

        messages = [
            {
                "role": "system",
                "content": document_prompt.format(
                    template=markdown_template,
                    date=transcription.created_datetime.strftime("%A %d %B %Y %H:%M:%S"),
                ),
            },
            get_transcript_messages(transcription.dialogue_entries or []),
        ]
        chatbot = create_default_chatbot(FastOrBestLLM.BEST)
        response = await chatbot.chat(messages)
        hallucinations = await chatbot.hallucination_check()
        return response, hallucinations
    else:
        qa_pairs: list[tuple[str, str]] = []
        for question in template.questions:
            chatbot = create_default_chatbot(FastOrBestLLM.FAST)
            if len(qa_pairs) > 0:
                previous_questions = "\n\n".join(f"## {q}\n{a}" for (q, a) in qa_pairs)
            else:
                previous_questions = "This is the first question."

            if question.description.strip():
                question_description = f"<question_description>{question.description.strip()}</question_description>"
            else:
                question_description = ""

            messages = [
                {
                    "role": "user",
                    "content": form_system_prompt,
                },
                {
                    "role": "user",
                    "content": form_prompt.format(
                        transcript=transcript_as_speaker_and_utterance(transcription.dialogue_entries or []),
                        style_guide=template.content,
                        previous_questions=previous_questions,
                        current_question=question.title,
                        question_description=question_description,
                    ),
                },
            ]
            resp = await chatbot.chat(messages)
            qa_pairs.append((question.title, resp))

        minute = "\n\n".join(f"## {q}\n{a}" for (q, a) in qa_pairs)

        return minute, []
