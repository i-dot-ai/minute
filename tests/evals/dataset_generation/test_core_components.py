from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from evals.dataset_generation.transcription_generation.src.actor import Actor, strip_speaker_prefix
from evals.dataset_generation.transcription_generation.src.actor_generator import ActorGenerator
from evals.dataset_generation.transcription_generation.src.facilitator import Facilitator
from evals.dataset_generation.transcription_generation.src.history_manager import HistoryManager
from evals.dataset_generation.transcription_generation.src.models import (
    ActorDefinition,
    ChatEntry,
    FacilitatorDecision,
)
from evals.dataset_generation.transcription_generation.src.participant import Participant


class FakeChatBot:
    def __init__(self, responses):
        self.responses = responses
        self.messages = []
        self.index = 0

    async def chat(self, messages):
        self.messages.append(messages)
        response = self.responses[self.index]
        self.index += 1
        return response


class ConcreteParticipant(Participant):
    @property
    def system_message_content(self) -> str:
        return "Test system message"


@pytest.fixture
def history_manager():
    return HistoryManager()


@pytest.fixture
def mock_chatbot():
    chatbot = AsyncMock()
    chatbot.messages = []
    return chatbot


def test_strip_speaker_prefix():
    assert strip_speaker_prefix("speaker_1 said: Hello world") == "Hello world"
    assert strip_speaker_prefix("No prefix here") == "No prefix here"


def test_actor_initialization(history_manager, mock_chatbot):
    actor = Actor(
        identifier="speaker_1",
        history_manager=history_manager,
        actor_definition="A friendly doctor",
        chatbot=mock_chatbot,
    )

    assert actor.identifier == "speaker_1"
    assert actor.history_manager is history_manager
    assert actor.actor_definition == "A friendly doctor"


@pytest.mark.asyncio
async def test_actor_reply_to_last_message_adds_to_history(history_manager, mock_chatbot):
    mock_chatbot.chat.return_value = "Hello patient!"

    actor = Actor(
        identifier="doctor",
        history_manager=history_manager,
        actor_definition="Doctor role",
        chatbot=mock_chatbot,
    )

    reply = await actor.reply_to_last_message("Patient says hello")

    assert reply == "Hello patient!"
    assert len(history_manager.history) == 1
    assert history_manager.history[0].speaker_id == "doctor"
    assert history_manager.history[0].content == "Hello patient!"


@pytest.mark.asyncio
async def test_actor_reply_strips_speaker_prefix(history_manager, mock_chatbot):
    mock_chatbot.chat.return_value = "speaker_1 said: I understand your concern"

    actor = Actor(
        identifier="speaker_1",
        history_manager=history_manager,
        actor_definition="Counselor",
        chatbot=mock_chatbot,
    )

    reply = await actor.reply_to_last_message("I'm worried")

    assert reply == "I understand your concern"
    assert history_manager.history[0].content == "I understand your concern"


@pytest.mark.asyncio
async def test_generate_actor_definitions_returns_list_of_strings(mock_chatbot):
    expected_definitions = ["Doctor in emergency room", "Patient with injury"]
    mock_response = ActorDefinition(actors_definitions=expected_definitions)
    mock_chatbot.structured_chat.return_value = mock_response

    generator = ActorGenerator(chatbot=mock_chatbot)
    result = await generator.generate_actor_definitions(theme="Medical emergency", num_speakers=2)

    assert result == expected_definitions
    assert len(result) == 2


@pytest.mark.asyncio
async def test_generate_actor_definitions_calls_structured_chat_with_correct_format(mock_chatbot):
    mock_response = ActorDefinition(actors_definitions=["Actor 1", "Actor 2"])
    mock_chatbot.structured_chat.return_value = mock_response

    generator = ActorGenerator(chatbot=mock_chatbot)
    await generator.generate_actor_definitions(theme="Business meeting", num_speakers=2)

    call_args = mock_chatbot.structured_chat.call_args
    messages_arg = call_args[0][0]
    response_format_arg = call_args[1]["response_format"]

    assert isinstance(messages_arg, list)
    assert messages_arg[0]["role"] == "system"
    assert response_format_arg == ActorDefinition


def test_facilitator_initialization(history_manager):
    actor_definitions = ["Doctor", "Patient"]
    speaker_ids = {"speaker_1", "speaker_2"}

    facilitator = Facilitator(
        history_manager=history_manager,
        actor_definitions=actor_definitions,
        speaker_ids=speaker_ids,
    )

    assert facilitator.identifier == "facilitator"
    assert facilitator.actor_definitions == actor_definitions
    assert facilitator.speaker_ids == speaker_ids


def test_build_facilitator_messages_with_history(history_manager, mock_chatbot):
    actor_definitions = ["Doctor", "Patient"]
    speaker_ids = {"speaker_1", "speaker_2"}

    history_manager.add_to_history("Hello doctor", "speaker_1")
    history_manager.add_to_history("Hello patient", "speaker_2")

    facilitator = Facilitator(
        history_manager=history_manager,
        actor_definitions=actor_definitions,
        speaker_ids=speaker_ids,
        chatbot=mock_chatbot,
    )

    messages = facilitator._build_facilitator_messages()  # noqa: SLF001

    assert messages[0]["role"] == "system"
    user_messages = [m for m in messages if m["role"] == "user"]
    assert any("Speaker speaker_1 said: Hello doctor" in m["content"] for m in user_messages)
    assert any("decide which speaker should speak next" in m["content"].lower() for m in user_messages)


def test_build_facilitator_messages_includes_reminder_for_unspoken_speakers(history_manager, mock_chatbot):
    actor_definitions = ["Doctor", "Patient"]
    speaker_ids = {"speaker_1", "speaker_2"}

    history_manager.add_to_history("Hello", "speaker_1")

    facilitator = Facilitator(
        history_manager=history_manager,
        actor_definitions=actor_definitions,
        speaker_ids=speaker_ids,
        chatbot=mock_chatbot,
    )

    messages = facilitator._build_facilitator_messages()  # noqa: SLF001
    user_messages = [m for m in messages if m["role"] == "user"]

    assert any("speaker_2" in m["content"] for m in user_messages)


@pytest.mark.asyncio
async def test_decide_next_speaker_returns_speaker_and_termination_flag(history_manager, mock_chatbot):
    actor_definitions = ["Doctor", "Patient"]
    speaker_ids = {"speaker_1", "speaker_2"}

    mock_decision = FacilitatorDecision(next_speaker_id="speaker_2", should_terminate=False)
    mock_chatbot.structured_chat.return_value = mock_decision

    facilitator = Facilitator(
        history_manager=history_manager,
        actor_definitions=actor_definitions,
        speaker_ids=speaker_ids,
        chatbot=mock_chatbot,
    )

    next_speaker, should_terminate = await facilitator.decide_next_speaker()

    assert next_speaker == "speaker_2"
    assert should_terminate is False
    mock_chatbot.structured_chat.assert_called_once()


@pytest.mark.asyncio
async def test_decide_next_speaker_calls_structured_chat_with_correct_format(history_manager, mock_chatbot):
    actor_definitions = ["Doctor", "Patient"]
    speaker_ids = {"speaker_1", "speaker_2"}

    mock_decision = FacilitatorDecision(next_speaker_id="speaker_1", should_terminate=False)
    mock_chatbot.structured_chat.return_value = mock_decision

    facilitator = Facilitator(
        history_manager=history_manager,
        actor_definitions=actor_definitions,
        speaker_ids=speaker_ids,
        chatbot=mock_chatbot,
    )

    await facilitator.decide_next_speaker()

    call_args = mock_chatbot.structured_chat.call_args
    messages_arg = call_args[0][0]
    response_format_arg = call_args[1]["response_format"]

    assert isinstance(messages_arg, list)
    assert response_format_arg == FacilitatorDecision


def test_history_manager_initialization():
    history_manager = HistoryManager()
    assert history_manager.history == []


def test_add_to_history_creates_chat_entry():
    history_manager = HistoryManager()
    history_manager.add_to_history("Hello world", "speaker_1")

    assert len(history_manager.history) == 1
    assert isinstance(history_manager.history[0], ChatEntry)
    assert history_manager.history[0].speaker_id == "speaker_1"
    assert history_manager.history[0].content == "Hello world"


def test_get_history_for_participant_formats_messages_correctly():
    history_manager = HistoryManager()
    history_manager.add_to_history("Hello", "speaker_1")
    history_manager.add_to_history("Hi there", "speaker_2")

    result = history_manager.get_history_for_participant("speaker_1")

    assert len(result) == 2
    assert result[0]["role"] == "assistant"
    assert result[0]["content"] == "You said: Hello"
    assert result[1]["role"] == "user"
    assert result[1]["content"] == "speaker_2 said: Hi there"


def test_participant_get_new_messages_includes_system_and_history(history_manager, mock_chatbot):
    history_manager.add_to_history("Hello", "speaker_1")

    participant = ConcreteParticipant(
        identifier="speaker_1",
        history_manager=history_manager,
        chatbot=mock_chatbot,
    )

    messages = participant.get_new_messages()

    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "Test system message"
    assert len(messages) > 1


def test_participant_get_new_messages_with_notice(history_manager, mock_chatbot):
    participant = ConcreteParticipant(
        identifier="speaker_1",
        history_manager=history_manager,
        chatbot=mock_chatbot,
    )

    notice = "Please wrap up"
    messages = participant.get_new_messages(notice_message=notice)

    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == notice


def test_participant_get_new_messages_filters_cached_messages(history_manager, mock_chatbot):
    mock_chatbot.messages = [{"role": "system", "content": "Test system message"}]

    participant = ConcreteParticipant(
        identifier="speaker_1",
        history_manager=history_manager,
        chatbot=mock_chatbot,
    )

    messages = participant.get_new_messages()

    assert len(messages) == 0


def test_actor_definition_initialization():
    definitions = ["Doctor", "Patient"]
    actor_def = ActorDefinition(actors_definitions=definitions)

    assert actor_def.actors_definitions == definitions


def test_facilitator_decision_initialization():
    decision = FacilitatorDecision(next_speaker_id="speaker_1", should_terminate=False)

    assert decision.next_speaker_id == "speaker_1"
    assert decision.should_terminate is False


def test_facilitator_decision_default_should_terminate():
    decision = FacilitatorDecision(next_speaker_id="speaker_2")

    assert decision.should_terminate is False


def test_facilitator_decision_requires_next_speaker_id():
    with pytest.raises(ValidationError):
        FacilitatorDecision()


def test_chat_entry_initialization():
    entry = ChatEntry(speaker_id="speaker_1", content="Hello world")

    assert entry.speaker_id == "speaker_1"
    assert entry.content == "Hello world"


def test_chat_entry_requires_both_fields():
    with pytest.raises(ValidationError):
        ChatEntry(content="Missing speaker")

    with pytest.raises(ValidationError):
        ChatEntry(speaker_id="speaker_1")


@pytest.mark.asyncio
async def test_multiple_actors_share_history():
    history = HistoryManager()

    bot1 = FakeChatBot(["Actor 1 response"])
    bot2 = FakeChatBot(["Actor 2 response"])

    actor1 = Actor(
        identifier="speaker_1",
        history_manager=history,
        actor_definition="Actor 1",
        chatbot=bot1,
    )

    actor2 = Actor(
        identifier="speaker_2",
        history_manager=history,
        actor_definition="Actor 2",
        chatbot=bot2,
    )

    await actor1.reply_to_last_message()
    await actor2.reply_to_last_message()

    assert len(history.history) == 2
    assert history.history[0].speaker_id == "speaker_1"
    assert history.history[1].speaker_id == "speaker_2"


@pytest.mark.asyncio
async def test_doctor_patient_conversation():
    history = HistoryManager()

    doctor_bot = FakeChatBot(["Can you describe your symptoms?"])
    patient_bot = FakeChatBot(["I have a headache and fever."])

    doctor = Actor(
        identifier="doctor",
        history_manager=history,
        actor_definition="Doctor role definition",
        chatbot=doctor_bot,
    )

    patient = Actor(
        identifier="patient",
        history_manager=history,
        actor_definition="Patient role definition",
        chatbot=patient_bot,
    )

    history.add_to_history("Hello doctor", "patient")
    doctor_reply = await doctor.reply_to_last_message("Hello doctor")
    patient_reply = await patient.reply_to_last_message(doctor_reply)

    assert doctor_reply == "Can you describe your symptoms?"
    assert patient_reply == "I have a headache and fever."


@pytest.mark.asyncio
async def test_three_actor_conversation():
    history = HistoryManager()

    actor1_bot = FakeChatBot(["I agree with that point"])
    actor2_bot = FakeChatBot(["Let me add something"])
    actor3_bot = FakeChatBot(["That's a good perspective"])

    actor1 = Actor(
        identifier="speaker_1",
        history_manager=history,
        actor_definition="First participant",
        chatbot=actor1_bot,
    )
    actor2 = Actor(
        identifier="speaker_2",
        history_manager=history,
        actor_definition="Second participant",
        chatbot=actor2_bot,
    )
    actor3 = Actor(
        identifier="speaker_3",
        history_manager=history,
        actor_definition="Third participant",
        chatbot=actor3_bot,
    )

    history.add_to_history("Let's start the discussion", "speaker_1")

    reply1 = await actor1.reply_to_last_message()
    reply2 = await actor2.reply_to_last_message()
    reply3 = await actor3.reply_to_last_message()

    assert reply1 == "I agree with that point"
    assert reply2 == "Let me add something"
    assert reply3 == "That's a good perspective"
    assert len(history.history) == 4


@pytest.mark.asyncio
async def test_conversation_history_accumulates():
    history = HistoryManager()

    actor1_bot = FakeChatBot(["Response 1", "Response 2"])
    actor2_bot = FakeChatBot(["Response A", "Response B"])

    actor1 = Actor(identifier="speaker_1", history_manager=history, actor_definition="Actor 1", chatbot=actor1_bot)
    actor2 = Actor(identifier="speaker_2", history_manager=history, actor_definition="Actor 2", chatbot=actor2_bot)

    await actor1.reply_to_last_message()
    assert len(history.history) == 1

    await actor2.reply_to_last_message()
    assert len(history.history) == 2

    await actor1.reply_to_last_message()
    assert len(history.history) == 3

    await actor2.reply_to_last_message()
    assert len(history.history) == 4
