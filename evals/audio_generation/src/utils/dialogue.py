from dataclasses import dataclass


@dataclass
class DialogueEntry:
    speaker: str
    text: str
    start_time: float
    end_time: float
