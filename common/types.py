import uuid
from datetime import datetime
from enum import IntEnum, StrEnum, auto

from pydantic import BaseModel, Field

from common.database.postgres_models import ContentSource, DialogueEntry, HallucinationType, JobStatus


class TranscriptionMetadata(BaseModel):
    """Pydantic model for transcription metadata."""

    id: uuid.UUID
    created_datetime: datetime
    title: str | None = None
    text: str
    status: JobStatus


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


class ChatCreateRequest(BaseModel):
    user_content: str


class ChatGetResponse(BaseModel):
    id: uuid.UUID
    created_datetime: datetime
    updated_datetime: datetime
    user_content: str
    assistant_content: str | None
    status: JobStatus


class ChatGetAllResponse(BaseModel):
    chat: list[ChatGetResponse]


class ChatCreateResponse(BaseModel):
    id: uuid.UUID


class GetUserResponse(BaseModel):
    id: uuid.UUID
    created_datetime: datetime
    updated_datetime: datetime
    email: str
    data_retention_days: int | None
    strict_data_retention: bool


class DataRetentionUpdateResponse(BaseModel):
    data_retention_days: int | None


class TranscriptionGetResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    dialogue_entries: list[DialogueEntry] | None
    status: JobStatus
    created_datetime: datetime


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
    template_name: str = Field(description="Name of the template to use for the minutes")
    template_id: uuid.UUID | None = Field(description="Optional id of user template")
    agenda: str | None = Field(description="The agenda for the meeting", default=None)


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


class TranscriptionJobResponse(BaseModel):
    status: JobStatus
    dialogue_entries: list["DialogueEntry"] | None = None
    error: str | None = None
    message: str | None = None
    id: uuid.UUID | None = None
    uploaded_documents: list[dict] | None = None
    upload_url: str | None = None
    user_upload_s3_file_key: str | None = None


class MinuteVersionResponse(BaseModel):
    id: uuid.UUID
    minute_id: uuid.UUID
    status: JobStatus
    created_datetime: datetime
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
    # messages have a natural ordering in which we want them to happen
    TRANSCRIPTION = 1
    MINUTE = 2
    EDIT = 3
    INTERACTIVE = 4


class EditMessageData(BaseModel):
    source_id: uuid.UUID = Field(description="ID of the source message")


class TranscriptionJobMessageData(BaseModel):
    transcription_service: str = Field(description="Name of the transcription service")
    job_name: str = Field(
        description="job name to identify asynchronous jobs. Not used in case of synchronous jobs",
        default="synchronous",
    )
    transcript: list[DialogueEntry] | None = Field(description="Transcript of the transcription", default=None)


class WorkerMessage(BaseModel):
    id: uuid.UUID
    type: TaskType
    data: EditMessageData | TranscriptionJobMessageData | None = Field(default=None)


class LLMHallucination(BaseModel):
    hallucination_type: HallucinationType = Field(description="Type of hallucination")
    hallucination_text: str | None = Field(description="Text of hallucination", default=None)
    hallucination_reason: str | None = Field(description="Reason for hallucination", default=None)


MinuteAndHallucinations = tuple[str, list[LLMHallucination] | None]


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


class PatchUserTemplateRequest(BaseModel):
    name: str | None = None
    content: str | None = None
    description: str | None = None


class CreateUserTemplateRequest(BaseModel):
    name: str
    content: str
    description: str
