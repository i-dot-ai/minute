import pytest
from evals.dataset_generation.transcription_generation.src.participant import ChatEntry, HistoryManager, Actor, Participant
from unittest.mock import AsyncMock

class FakeChatBot:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.index = 0

    async def chat(self, messages):
        self.calls.append(messages)
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

    history.add_to_history("Hello", "doctor")
    history.add_to_history("Hi doctor", "patient")

    result = history.get_history_for_participant("doctor")

    assert result == [
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "Hi doctor"},
    ]


@pytest.mark.asyncio
async def test_actor_reply_mock():
    history = HistoryManager()

    mock_bot = AsyncMock()
    mock_bot.chat.return_value = "Mocked response"

    actor = Actor(
        identifier="doctor",
        history_manager=history,
        actor_definition="Doctor",
        chatbot=mock_bot,
    )

    response = await actor.reply_to_last_message("Hello")

    assert history.history[-1] == ChatEntry(
    speaker_id="doctor",
    content="Mocked response"
    )
    mock_bot.chat.assert_called_once()