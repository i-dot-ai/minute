import pytest
from evals.dataset_generation.transcription_generation.src.participant import ChatEntry, HistoryManager, Actor, Participant
from unittest.mock import AsyncMock

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



@pytest.mark.asyncio
async def test_actor_reply_adds_to_history():

    history = HistoryManager()

    fake_bot = FakeChatBot(["Hello patient!"])

    actor = Actor(
        identifier="doctor",
        history_manager=history,
        actor_definition="Doctor role definition",
        chatbot=fake_bot,
    )

    reply = await actor.reply_to_last_message("Patient says hello")

    assert reply == "Hello patient!"
    assert history.history == [
        ChatEntry(speaker_id="doctor", content="Hello patient!")
    ]


def test_history_role_mapping():
    history = HistoryManager()

    ROLE_ONE = "doctor"
    ROLE_TWO = "patient"

    history.add_to_history("Hello", ROLE_ONE)
    history.add_to_history("Hi doctor", ROLE_TWO)

    result = history.get_history_for_participant(ROLE_ONE)

    assert result == [
        {"role": "assistant", "content": "You said: Hello"},
        {"role": "user", "content": "patient said: Hi doctor"},
    ]


@pytest.mark.asyncio
async def test_actor_reply_mock():
    history = HistoryManager()

    mock_bot = AsyncMock()
    mock_bot.chat.return_value = "How are you?"

    actor = Actor(
        identifier="doctor",
        history_manager=history,
        actor_definition="Doctor",
        chatbot=mock_bot,
    )

    response = await actor.reply_to_last_message("Hello")

    assert history.history[-1] == ChatEntry(
    speaker_id="doctor",
    content="How are you?"
    )
    mock_bot.chat.assert_called_once()