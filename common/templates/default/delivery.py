# flake8: noqa: E501, RUF001
from pydantic import BaseModel, Field

from common.database.postgres_models import DialogueEntry, Minute
from common.llm.client import FastOrBestLLM, create_default_chatbot
from common.prompts import get_transcript_messages
from common.templates.citations import add_citations_to_minute
from common.templates.types import Template
from common.types import AgendaUsage, MinuteAndHallucinations


class DeliveryMeetingSection(BaseModel):
    section_name: str = Field(description="Name of the section")
    section_text: str = Field(description="summary of the discussion for the section")
    action_items: list[str] = Field(description="list of action items for the section")


class DeliveryMeetingSections(BaseModel):
    sections_list: list[DeliveryMeetingSection] = Field(
        description="A list of distinct discussion topics or agenda items covered during a formal meeting, such as 'Opening Remarks', 'Previous Actions Review', 'Main Discussion Points', 'Action Items', or 'Closing Summary'. Must be in the order they appear in the transcript.",
        default_factory=list,
    )


class Attendee(BaseModel):
    name: str = Field(description="Name of the attendee")
    role: str = Field(description="Role of the attendee")


class AttendeeList(BaseModel):
    attendees: list[Attendee] = Field(description="List of attendees")


class Delivery(Template):
    name = "Delivery"
    category = "Formal Minutes"
    description = "Formal minutes following the delivery style guide"
    agenda_usage = AgendaUsage.NOT_USED

    style_guide = """
- The minute is written in past reported speech.
- The minute is written entirely in British English.
- On the first instance of referencing an individual in the “Record of Discussion” section minute, use the full name, with the initials in brackets. Thereafter, use the initials to reference that individual if the full name of the individual is known.
- Reference all departments by their abbreviation.
- Citations should be of the form [n] where n is the index of the transcript item. Each citation should be one number surrounded by square brackets. For example, you must do [80][81] not [80, 81]
- Each section must have a heading.
- The output should be in plain text format."""

    @classmethod
    def get_system_message_for_delivery(cls, transcript: list[DialogueEntry]) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": """You are an AI meeting assistant. Your task is to extract and summarise different aspects of a meeting based on a transcript of a meeting.""",
            },
            get_transcript_messages(transcript),
        ]

    @classmethod
    def get_messages_for_sections(cls) -> dict[str, str]:
        return {
            "role": "user",
            "content": f"""Generate a list of sections that the meeting should be split into.
The sections should be in the order they appear in the transcript. Typically you will at least have an introduction and a conclusion. Use the following style guide to guide you:
{cls.style_guide}""",
        }

    @classmethod
    def get_messages_for_attendees(cls) -> dict[str, str]:
        return {"role": "user", "content": "Your task is to now extract a list of attendees from the meeting"}

    @classmethod
    async def generate(
        cls,
        minute: Minute,
    ) -> MinuteAndHallucinations:
        chatbot = create_default_chatbot(FastOrBestLLM.BEST)
        initial_messages = cls.get_system_message_for_delivery(minute.transcription.dialogue_entries)
        # meeting sections
        initial_messages.append(cls.get_messages_for_sections())
        sections: DeliveryMeetingSections = await chatbot.structured_chat(
            initial_messages, response_format=DeliveryMeetingSections
        )
        hallucinations = await chatbot.hallucination_check()
        # attendees
        attendee_list = await chatbot.structured_chat([cls.get_messages_for_attendees()], response_format=AttendeeList)

        header = "### Attendees:\n"
        for attendee in attendee_list.attendees:
            header += f"{attendee.name}:\t{attendee.role}\n"

        header += "\n\n### Summary of Actions:\n"

        initial_draft = "\n\n### Record of Discussion:\n\n"
        action_index = 1
        for section in sections.sections_list:
            initial_draft += f"### {section.section_name}\n"
            initial_draft += f"{section.section_text}\n"
            for action in section.action_items:
                action_block = f"ACTION {action_index}: {action}\n"
                header += action_block
                initial_draft += action_block
                action_index += 1

        final = header + "\n\n" + initial_draft
        final = await add_citations_to_minute(transcript=minute.transcription.dialogue_entries, initial_draft=final)
        return final, hallucinations
