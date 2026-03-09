from pydantic import BaseModel, Field


class ActorDefinition(BaseModel):
    actors_definitions: list[str] = Field(description="List of detailed actor definitions for role-playing")
