from common.database.postgres_models import DialogueEntry
from common.prompts import get_transcript_messages


class UserMarkdownTemplate:
    @classmethod
    def prompt(cls, template: str, transcript: list[DialogueEntry]) -> list[dict[str, str]]:
        prompt = f"""<task>
You are an expert meeting minutes writer with extensive experience across various sectors. \
Your task is to create clear, comprehensive, and well-structured meeting minutes that capture \
both the essence and important details of the discussion.

Transform the provided meeting content into structured minutes following the template guidelines precisely.
</task>

<requirements>
- Follow the structure outlined in the <template> section below exactly. \
Do not add additonal sections if they are not specified.
- Follow any style guidelines exactly.
- Write in British (UK) English unless otherwise specified
- Use clear, professional language unless otherwise specified
- Ensure proper use of UK government-specific terminology (e.g., "COBR" not "Cobra")
</requirements>

<template>

{template}

</template>

"""

        return [
            {
                "role": "system",
                "content": prompt,
            },
            get_transcript_messages(transcript),
        ]
