import markdownify

from common.database.postgres_models import DialogueEntry, Transcription
from common.prompts import get_transcript_messages

prompt = """<task>
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


class UserMarkdownTemplate:
    @classmethod
    def prompt(
        cls, template: str, transcript: list[DialogueEntry], transcription: Transcription
    ) -> list[dict[str, str]]:
        markdown_template = markdownify.markdownify(template, heading_style=markdownify.ATX)

        return [
            {
                "role": "system",
                "content": prompt.format(
                    template=markdown_template,
                    date=transcription.created_datetime.strftime("%A %d %B %Y %H:%M:%S"),
                ),
            },
            get_transcript_messages(transcript),
        ]
