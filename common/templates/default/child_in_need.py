# child_in_need.py
# flake8: noqa: E501, RUF001
#
# Transcript template notes:
# Apologies not included (these would require identifying missing participants which may be difficult to do reliably).

from common.database.postgres_models import DialogueEntry
from common.format_transcript import transcript_as_speaker_and_utterance
from common.settings import get_settings
from common.templates.types import SimpleTemplate
from common.types import AgendaUsage


settings = get_settings()


class ChildInNeedMeeting(SimpleTemplate):
    name = "Child in Need Meeting/Plan Review"
    category = "Social Care"
    description = "Child in Need meeting and plan review template based on RBKC 2026 Child in Need Meeting/Plan Review template"
    citations_required = True
    agenda_usage = AgendaUsage.NOT_USED
    temperature = 0.0

    @classmethod
    def prompt(cls, transcript: list[DialogueEntry], agenda: str | None = None) -> list[dict[str, str]]:  # noqa: ARG003
        return [
            {
                "role": "system",
                "content": """You are an experienced social worker in the UK. You are helping to complete a Child in Need Meeting record and plan review. You are helping to compile the information required to write the meeting record based on the transcript of the meeting.
Here are the general guidelines to follow:
Write in the third person for children, young people, and family members.
Focus on documenting the actual conversation and agreed actions from the meeting.
Important: do not make any analysis, assumptions or judgements about the child, young person, or family's circumstances beyond what is stated. Be descriptive only based on the content of the transcript.
Include quotes from participants if they support the section being completed.
Provide as much detail as possible.
Do not include information not provided in the transcript.
Do not hallucinate any information that is not in the transcript. If the transcript does not contain information for a section, you do not need to write anything. It is also fine to have a very short section if there is not enough information to write a full section.
Use the information in curly brackets {} to help you decide what information to include in each section. Do not include anything in curly brackets {} in the output text.
Follow the following format, adding as much detail as possible under each heading:


# Child / young person's details

{Provide details of all subject children and young people discussed in the meeting using bullet point for their name and then sub-bullet points for characteristics: date of birth or expected delivery date, age, gender, ethnicity and religion where mentioned.}


# Family / household composition and significant others (e.g. maternal / paternal grandparents, aunts, uncles)

{Who lives in the household? Include all family members and significant others such as maternal or paternal grandparents, aunts, and uncles. For each person, note their name as the top bullet point and then sub-bullet points for date of birth, gender, whether they hold parental responsibility, whether they live in the household, and their relationship to the child.}


# Communication needs (including language)

{Are there any communication needs for the child, young person, or family members, including language needs, interpreters required, or any other communication support? Note any languages spoken and any accessibility requirements.}


# Relevant legal status and immigration status for any family household member or significant people not living in the household

{Are there any relevant legal orders in place, such as Child in Need plans, Child Protection plans, Care Orders, or Supervision Orders? Is there any relevant immigration status for any family member or significant person not living in the household?}


# Record of Review Meeting

## Date of this meeting / plan review

{Use the date of the meeting as stated in the transcript, otherwise write "Date not specified."}

## People involved in developing this plan

{- Name, - Relationship to the child, - Role/Agency (Key Worker). Use bullet points for each person involved in developing the plan.}

## Apologies

{- Name, Relationship to the child, - Role/Agency (Key Worker). It is unlikely you will be able to fill this section as it requires identifying missing participants which may be difficult to do reliably. If you cannot identify any apologies from the transcript, write "No apologies identified from the transcript."}


# Record of Meeting

## Purpose of Meeting

{What was the stated purpose of this meeting or plan review? Is this an initial Child in Need meeting or a review? What is the overarching aim?}


## Extra Familial Harm

{Is any child or young person at risk of extra familial harm? Was an Adolescents Risk Tool discussed? Note any relevant concerns raised in the meeting about contextual or extra familial risks such as county lines, exploitation, peer violence, or online risks.}


## Record of Discussion

{What was discussed during the meeting? Summarise the key points raised by professionals, family members, and the child or young person where present. Include any updates on the child's welfare, progress against previous plan actions, and any new concerns or changes in circumstances. Note any disagreements or differing views between participants.}


# Details of the Plan

## Purpose of This Plan

{What is the purpose of the current Child in Need plan? What are the overarching goals for the child and family?}


## Plan Actions

{What actions were agreed during this meeting? For each action, note: which child or young person it relates to; what the concern or need is; what needs to happen; who is responsible (family member, professional, or other); the timescale or deadline; and any update on progress from a previous plan. Where the transcript references completion of previous actions, note these separately.}


## Next Review

{When is the next meeting or review planned? Who should be invited? Are there any particular matters to be carried over to the next review?}

""",
            },
            {"role": "user", "content": transcript_as_speaker_and_utterance(transcript)},
        ]
