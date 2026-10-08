import uuid
from datetime import datetime
from enum import IntEnum, StrEnum, auto

from pydantic import BaseModel, Field

from common.database.postgres_models import ContentSource, DialogueEntry, JobStatus, TemplateType


class TranscriptionListFilter(StrEnum):
    EXPIRING_SOON = "expiring-soon"
    FAILED = "failed"


class TranscriptionMetadata(BaseModel):
    """Pydantic model for transcription metadata."""

    id: uuid.UUID
    created_datetime: datetime
    title: str | None = None
    text: str
    status: JobStatus
    expiring: bool


class PaginatedTranscriptionsResponse(BaseModel):
    """Paginated response for transcriptions."""

    items: list[TranscriptionMetadata]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class TranscriptionCreateRequest(BaseModel):
    recording_id: uuid.UUID
    template_name: str
    template_id: uuid.UUID | None = None
    agenda: str | None = None
    title: str | None = None


class TranscriptionRetryRequest(BaseModel):
    template_name: str
    template_id: uuid.UUID | None = None
    agenda: str | None = None


class RecordingCreateRequest(BaseModel):
    file_extension: str


class RecordingCreateResponse(BaseModel):
    id: uuid.UUID
    upload_url: str


class TranscriptionCreateResponse(BaseModel):
    id: uuid.UUID


class TranscriptionConfirmResponse(BaseModel):
    id: uuid.UUID


class TranscriptionPatchRequest(BaseModel):
    title: str | None = None
    dialogue_entries: list[DialogueEntry] | None = None


class GetUserResponse(BaseModel):
    id: uuid.UUID
    created_datetime: datetime
    updated_datetime: datetime
    email: str
    data_retention_days: int | None
    default_template_id: uuid.UUID | None = None
    default_template_name: str | None = None


class DataRetentionUpdateResponse(BaseModel):
    data_retention_days: int | None


class SetDefaultTemplateRequest(BaseModel):
    template_id: uuid.UUID | None = None
    template_name: str | None = None


class TranscriptionGetResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    dialogue_entries: list[DialogueEntry] | None
    status: JobStatus
    created_datetime: datetime
    error: str | None = None


class SingleRecording(BaseModel):
    id: uuid.UUID
    url: str
    extension: str


class MinuteListItem(BaseModel):
    id: uuid.UUID
    created_datetime: datetime
    updated_datetime: datetime
    transcription_id: uuid.UUID
    template_name: str
    agenda: str | None


class MinutesCreateRequest(BaseModel):
    template_name: str | None = Field(description="Name of the template to use for the minutes", default=None)
    template_id: uuid.UUID | None = Field(description="Optional id of user template", default=None)
    agenda: str | None = Field(description="The agenda for the meeting", default=None)
    source_minute_id: uuid.UUID | None = Field(
        description="If set, copy template_name, user_template_id and agenda from this minute",
        default=None,
    )


class AiEdit(BaseModel):
    instruction: str
    source_id: uuid.UUID


class MinuteVersionCreateRequest(BaseModel):
    ai_edit_instructions: AiEdit | None = Field(
        default=None,
        description="If the content source is an AI edit, store the instruction and source version id here",
    )
    content_source: ContentSource
    html_content: str = Field(default="")


class MinutesPatchRequest(BaseModel):
    html_content: str | None = None


class MinuteVersionResponse(BaseModel):
    id: uuid.UUID
    minute_id: uuid.UUID
    status: JobStatus
    created_datetime: datetime
    updated_datetime: datetime
    html_content: str
    error: str | None
    ai_edit_instructions: str | None
    content_source: ContentSource


class SpeakerPrediction(BaseModel):
    original_speaker: str
    predicted_name: str
    confidence: float


class SpeakerPredictionOutput(BaseModel):
    predictions: list[SpeakerPrediction]


class MinutesResponse(BaseModel):
    minutes: str


class MeetingCheck(BaseModel):
    is_long_meeting: bool


class TaskType(IntEnum):
    MINUTE = 1
    EDIT = 2


class EditMessageData(BaseModel):
    source_id: uuid.UUID = Field(description="ID of the source message")


class WorkerMessage(BaseModel):
    id: uuid.UUID
    type: TaskType
    data: EditMessageData | None = Field(default=None)


class MeetingType(StrEnum):
    too_short = auto()
    short = auto()
    standard = auto()


class AgendaUsage(StrEnum):
    NOT_USED = auto()
    OPTIONAL = auto()
    REQUIRED = auto()


class TemplateMetadata(BaseModel):
    name: str
    description: str
    category: str
    agenda_usage: AgendaUsage
    is_default: bool = False


class CreateQuestion(BaseModel):
    position: int
    title: str
    description: str


class Question(CreateQuestion):
    id: uuid.UUID


class PatchUserTemplateRequest(BaseModel):
    name: str | None = None
    content: str | None = None
    description: str | None = None
    questions: list[CreateQuestion | Question] | None = None


class TemplateResponse(BaseModel):
    id: uuid.UUID
    updated_datetime: datetime
    name: str
    content: str
    description: str
    type: TemplateType
    questions: list[Question] | None
    is_default: bool = False


class CreateUserTemplateRequest(BaseModel):
    name: str
    content: str
    description: str
    type: TemplateType
    questions: list[CreateQuestion] | None = None
