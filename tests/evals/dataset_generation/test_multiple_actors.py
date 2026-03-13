import pytest

from evals.dataset_generation.transcription_generation.src.actor import Actor
from evals.dataset_generation.transcription_generation.src.history_manager import HistoryManager


class ScriptedChatBot:
    def __init__(self, responses):
        self.responses = responses
        self.index = 0
        self.messages = []

    async def chat(self, messages):
        self.messages.append(messages)

        response = self.responses[self.index]
        self.index += 1

        return response


@pytest.mark.asyncio
async def test_doctor_patient_conversation():
    history = HistoryManager()

    doctor_bot = ScriptedChatBot(["Can you describe your symptoms?"])

    patient_bot = ScriptedChatBot(["I have a headache and fever."])

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
