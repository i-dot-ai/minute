from datetime import datetime
from enum import StrEnum, auto
from typing import TypedDict
from uuid import UUID, uuid4

from pydantic import computed_field
from sqlalchemy import TIMESTAMP, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.sql.functions import now
from sqlmodel import Field, Relationship, SQLModel, col, func


class DialogueEntry(TypedDict):
    speaker: str
    text: str
    start_time: float
    end_time: float


# Create factory functions for columns to avoid reusing column objects
def created_datetime_column():
    return Column(TIMESTAMP(timezone=True), nullable=False, server_default=now(), default=None)


def updated_datetime_column():
    return Column(TIMESTAMP(timezone=True), nullable=False, server_default=now(), default=None)


class BaseTableMixin(SQLModel):
    # Note, we can't add created/updated_datetime Columns here, as each table needs its own instance of these Columns
    model_config = {  # noqa: RUF012
        "from_attributes": True,
    }

    id: UUID = Field(
        default_factory=uuid4, primary_key=True, sa_column_kwargs={"server_default": func.gen_random_uuid()}
    )


class JobStatus(StrEnum):
    AWAITING_START = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


class ContentSource(StrEnum):
    MANUAL_EDIT = auto()
    AI_EDIT = auto()
    INITIAL_GENERATION = auto()


class MinuteVersion(BaseTableMixin, table=True):
    __tablename__ = "minute_version"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    minute_id: UUID = Field(foreign_key="minute.id", ondelete="CASCADE")
    minute: Mapped["Minute"] = Relationship(back_populates="minute_versions")
    hallucinations: list["Hallucination"] = Relationship(back_populates="minute_version", cascade_delete=True)
    html_content: str = Field(default="", sa_column_kwargs={"server_default": ""})
    status: JobStatus = Field(
        default=JobStatus.AWAITING_START, sa_column_kwargs={"server_default": JobStatus.AWAITING_START.name}
    )
    error: str | None = None
    ai_edit_instructions: str | None = Field(
        default=None, description="If the content source is an AI edit, store the instruction here"
    )

    content_source: ContentSource = Field(
        default=ContentSource.INITIAL_GENERATION,
        sa_column_kwargs={"server_default": ContentSource.INITIAL_GENERATION.name},
    )


class Minute(BaseTableMixin, table=True):
    __tablename__ = "minute"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    transcription_id: UUID = Field(foreign_key="transcription.id", ondelete="CASCADE")
    transcription: Mapped["Transcription"] = Relationship(back_populates="minutes")
    template_name: str = Field(default="General")
    user_template_id: UUID | None = Field(
        foreign_key="user_template.id", nullable=True, ondelete="SET NULL", default=None
    )
    user_template: "UserTemplate" = Relationship(back_populates="minutes")
    agenda: str | None = Field(nullable=True, default=None)
    minute_versions: Mapped[list["MinuteVersion"]] = Relationship(
        back_populates="minute",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": col(MinuteVersion.created_datetime).desc()},
    )


class HallucinationType(StrEnum):
    FACTUAL_FABRICATION = auto()
    NONSENSICAL = auto()
    CONTRADICTION = auto()
    MISLEADING = auto()
    OTHER = auto()


class Hallucination(BaseTableMixin, table=True):
    __tablename__ = "hallucination"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    minute_version_id: UUID = Field(foreign_key="minute_version.id", ondelete="CASCADE")
    minute_version: MinuteVersion = Relationship(back_populates="hallucinations")
    hallucination_type: HallucinationType = Field(description="Type of hallucination", default=HallucinationType.OTHER)
    hallucination_text: str | None = Field(description="Text of hallucination", default=None)
    hallucination_reason: str | None = Field(description="Reason for hallucination", default=None)


# Main models with table=True for DB tables
class User(BaseTableMixin, table=True):
    __tablename__ = "user"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    email: str = Field(index=True)
    data_retention_days: int | None = Field(default=30)
    transcriptions: list["Transcription"] = Relationship(back_populates="user")

    @computed_field
    @property
    def strict_data_retention(self) -> bool:
        try:
            username, domain = self.email.split("@", maxsplit=1)
            return "cabinetoffice" in domain.lower() or "dsit" in domain.lower()
        except ValueError:
            return False


class Recording(BaseTableMixin, table=True):
    __tablename__ = "recording"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    user_id: UUID = Field(foreign_key="user.id", nullable=False)
    s3_file_key: str
    transcription_id: UUID | None = Field(default=None, foreign_key="transcription.id", ondelete="SET NULL")
    transcription: "Transcription" = Relationship(back_populates="recordings")


class Chat(BaseTableMixin, table=True):
    __tablename__ = "chat"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    transcription_id: UUID = Field(foreign_key="transcription.id", ondelete="CASCADE")
    transcription: Mapped["Transcription"] = Relationship(back_populates="chat")
    user_content: str = Field(default=None)
    assistant_content: str | None = Field(default=None)
    status: JobStatus = Field(
        default=JobStatus.AWAITING_START, sa_column_kwargs={"server_default": JobStatus.AWAITING_START.name}
    )
    error: str | None = Field(default=None)


class Transcription(BaseTableMixin, table=True):
    __tablename__ = "transcription"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    title: str | None = Field(default=None)
    dialogue_entries: list[DialogueEntry] | None = Field(default=None, sa_column=Column(JSONB))
    status: JobStatus = Field(
        default=JobStatus.AWAITING_START, sa_column_kwargs={"server_default": JobStatus.AWAITING_START.name}
    )
    error: str | None = Field(default=None)
    user: User | None = Relationship(back_populates="transcriptions")
    user_id: UUID | None = Field(default=None, foreign_key="user.id")
    minutes: list[Minute] = Relationship(
        back_populates="transcription",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": col(Minute.created_datetime).desc()},
    )

    # Kept old minute versions so we can migrate them
    legacy_minute_versions: list[dict] | None = Field(sa_column=Column(name="minute_versions", type_=JSONB), default=[])

    recordings: Mapped[list[Recording]] = Relationship(
        back_populates="transcription",
        sa_relationship_kwargs={"order_by": col(Recording.created_datetime).desc()},
    )
    chat: list[Chat] = Relationship(
        back_populates="transcription",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": col(Chat.created_datetime).desc()},
    )


class UserTemplate(BaseTableMixin, table=True):
    __tablename__ = "user_template"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)

    name: str
    content: str
    description: str = ""

    user_id: UUID | None = Field(default=None, foreign_key="user.id")

    minutes: list[Minute] = Relationship(back_populates="user_template")
