from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field


class TranscriptGenerationConfig(BaseModel):
    theme: str = Field(description="Theme or scenario for the conversation")
    word_target: int = Field(default=400, description="Target words in generated transcript")
    termination_threshold_multiplier: float = Field(
        default=1.25, description="Multiplier for word_target to determine hard termination (e.g., 1.25 = 125%)"
    )
    max_words_per_turn: int | None = Field(
        default=None, description="Maximum words to keep in conversation context per speaker (None = unlimited)"
    )
    num_speakers: int = Field(default=2, description="Number of speakers in conversation")

    @property
    def speaker_ids(self) -> list[str]:
        return [f"speaker_{i+1}" for i in range(self.num_speakers)]


class PromptConfig(BaseModel):
    prompts_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "prompts",
        description="Directory containing Jinja2 templates",
    )
    actor_generator_template: str = Field(
        default="actor_generator.j2", description="Template for generating actor definitions"
    )
    actor_system_template: str = Field(default="actor_system.j2", description="Template for actor system prompts")
    facilitator_template: str = Field(default="facilitator.j2", description="Template for facilitator prompts")
    time_remaining_template: str = Field(default="time_remaining.j2", description="Template for time remaining message")

    def create_environment(self) -> Environment:
        return Environment(loader=FileSystemLoader(self.prompts_dir), autoescape=select_autoescape())
