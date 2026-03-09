from pydantic import BaseModel, Field


class ActorDefinition(BaseModel):
    actors_definitions: list[str] = Field(description="List of detailed actor definitions for role-playing")


class FacilitatorDecision(BaseModel):
    next_speaker_id: str = Field(description="ID of the speaker who should speak next")
