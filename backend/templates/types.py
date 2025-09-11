from typing import Protocol

from backend.app.llm.client import create_chatbot
from backend.app.minutes.prompts import get_section_for_agenda_prompt, string_to_system_message
from backend.app.minutes.types import AgendaUsage, MinuteAndHallucinations
from backend.templates.template_utils import add_citations_to_minute
from common.database.postgres_models import DialogueEntry, Minute
from common.settings import get_settings

settings = get_settings()


class Template(Protocol):
    """Protocol for defining a template.

    This class describes the structure and required properties for templates,
    as well as the necessary method for generating `MinuteAndHallucinations`.
    Templates are categorized with specific metadata such as name, description,
    and category.

    Attributes:
        name: The name of the template.
        description: A brief description of the template.
        category: The category or grouping of the template.
        agenda_usage: Specifies the usage of the agenda within the template.

    """

    name: str
    description: str
    category: str
    agenda_usage: AgendaUsage
    provider = settings.LLM_PROVIDER
    model = settings.LLM_MODEL_NAME
    temperature = 0.0

    @classmethod
    async def generate(
        cls,
        minute: Minute,
    ) -> MinuteAndHallucinations:
        """
        Asynchronously generates a Minute and any potential Hallucinations.

        Args:
            minute (Minute): A `Minute` instance containing information for which
                data is to be generated.

        Returns:
            MinuteAndHallucinations: An object containing the processed Minute data
                and the generated hallucination-related information.
        """
        ...


class SimpleTemplate(Template, Protocol):
    """Template class for generating prompts and processing results for AI-driven dialogue.

    This class defines methods for creating prompts from dialogue entries and optional
    agendas, as well as handling the generation of structured outputs (like minutes)
    and identifying hallucinations in AI outputs. The class is particularly useful for
    workflows involving AI-generated summaries or structured text construction.

    Attributes:
        citations_required: Whether the generated minutes should include citations. This is appropriate for longer
            summaries.

    """

    citations_required: bool

    @classmethod
    def prompt(cls, transcript: list[DialogueEntry], agenda: str | None = None) -> list[dict[str, str]]:
        """
        Generates a formatted prompt based on a transcript of dialogue entries and an agenda.

        This method constructs a list of dictionaries representing parts of a prompt,
        which typically combines the given dialogue entries with a specific agenda if
        provided. It is intended for use cases where building prompts for AI.

        Args:
            transcript: A list of dialogue entries containing
                dialogue data to be included in the prompt.
            agenda: An optional agenda or topic that will influence the
                content or context of the prompt.

        Returns:
            list[dict[str, str]]: A list of dictionaries, where each dictionary contains
            structured prompt information based on the given transcript and agenda.
        """
        ...

    @classmethod
    async def generate(
        cls,
        minute: Minute,
    ) -> MinuteAndHallucinations:
        chatbot = create_chatbot(cls.provider, cls.model, temperature=cls.temperature)
        minutes = await chatbot.chat(cls.prompt(minute.transcription.dialogue_entries, minute.agenda))
        hallucinations = await chatbot.hallucination_check()
        if cls.citations_required:
            minutes = await add_citations_to_minute(
                transcript=minute.transcription.dialogue_entries, initial_draft=minutes
            )
        return minutes, hallucinations


class SectionTemplate(Template, Protocol):
    """Defines a SectionTemplate class for generating structured sections
    from transcripts and agendas.

    This class serves as a template for creating sections from dialogue
    entries and agendas, processing them via a chatbot system, and
    optionally incorporating citations. It provides methods for generating
    prompts, creating sections, and generating a final structured draft
    with additional features like hallucination check and citation
    inclusion. It is useful for elucidating more detail on the specified sections than the standard SimpleTemplate.

    Attributes:
        citations_required (bool): Specifies if citations are required for
            the minutes.

    """

    citations_required: bool

    @classmethod
    def system_prompt(cls, transcript: list[DialogueEntry]) -> str:
        """Constructs the initial system prompt based on the dialogue transcript.

        This class method processes a list of dialogue entries and generates a
        formatted string that can be used as a prompt for a system to initiate or
        continue a conversation.

        Args:
            transcript: A chronological list of dialogue
                entries representing the conversation history.

        Returns:
            str: A formatted string representing the system prompt constructed
            from the given transcript.
        """
        ...

    @classmethod
    async def sections(cls, transcript: list[DialogueEntry] | None = None, agenda: str | None = None) -> list[str]:
        """
        Generates a list of sections based on the provided transcript and agenda.

        This method processes the given transcript and agenda to categorize or
        break them into meaningful sections.

        Args:
            transcript: A list of DialogueEntry objects containing dialogue
                details for analysis. If not provided, defaults to None.
            agenda: An optional string describing the agenda of the conversation
                or discussion.

        Returns:
            A list of strings representing the computed or categorized sections.
        """
        ...

    @classmethod
    async def generate(
        cls,
        minute: Minute,
    ) -> MinuteAndHallucinations:
        transcript = minute.transcription.dialogue_entries
        sections = await cls.sections(transcript, minute.agenda)
        # Generate content for each section
        final_sections = []
        all_hallucinations = []
        chatbot = create_chatbot(cls.provider, cls.model, temperature=cls.temperature)
        for i, section in enumerate(sections):
            if i == 0:
                # use system message exactly once
                section_contents = await chatbot.chat(
                    [
                        string_to_system_message(cls.system_prompt(transcript)),
                        get_section_for_agenda_prompt(section),
                    ]
                )
                final_sections.append(section_contents)
                all_hallucinations = await chatbot.hallucination_check()
            else:
                section_contents = await chatbot.chat([get_section_for_agenda_prompt(section)])
                final_sections.append(section_contents)
                hallucinations = await chatbot.hallucination_check()
                all_hallucinations.extend(hallucinations)

        initial_draft = "\n".join(final_sections)
        if cls.citations_required:
            final_minutes = await add_citations_to_minute(transcript=transcript, initial_draft=initial_draft)
        else:
            final_minutes = initial_draft

        return final_minutes, all_hallucinations
