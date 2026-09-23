import uuid
from datetime import datetime
from enum import IntEnum, StrEnum, auto

from pydantic import BaseModel, Field, model_validator

from common.database.postgres_models import (
    ContentSource,
    DialogueEntry,
    HallucinationType,
    JobStatus,
    TemplateType,
    User,
)


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
    default_template_id: uuid.UUID | None = None
    default_template_name: str | None = None

    @classmethod
    def from_user(cls, user: User):
        return cls(
            id=user.id,
            created_datetime=user.created_datetime,
            updated_datetime=user.updated_datetime,
            email=user.email,
            data_retention_days=user.data_retention_days,
            default_template_id=user.default_template_id,
            default_template_name=user.default_template_name,
        )


class UpdateDataRetentionReq(BaseModel):
    data_retention_days: int | None = Field(default=None, gt=0)


class SetDefaultTemplateRequest(BaseModel):
    template_id: uuid.UUID | None = None
    template_name: str | None = None

    @model_validator(mode="after")
    def check_mutually_exclusive(self):
        if self.template_id is not None and self.template_name is not None:
            msg = "Provide either template_id or template_name, not both"
            raise ValueError(msg)
        return self


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
    template_name: str | None = None
    template_id: uuid.UUID | None = None
    agenda: str | None = None
    source_minute_id: uuid.UUID | None = None  # Copy if set

    @model_validator(mode="after")
    def check_mutually_exclusive(self):
        if self.source_minute_id is None and self.template_name is None:
            msg = "Provide either source_minute_id or template_name"
            raise ValueError(msg)
        return self


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
    # messages have a natural ordering in which we want them to happen
    AUDIO_PREPROCESSING = 0
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


class PipelineStageStatus(BaseModel):
    """Status of a single stage in the recording -> transcription -> minute pipeline."""

    stage: str = Field(description="Stage name, e.g. 'preprocessing', 'transcription', 'minute_generation'")
    status: str = Field(description="Stage status derived from DB state")
    detail: str | None = Field(default=None, description="Human-readable explanation of the current state")
    updated_datetime: datetime | None = Field(default=None, description="When this stage's record last changed")


class QueueDepth(BaseModel):
    name: str
    visible: int = Field(description="Messages waiting to be picked up")
    in_flight: int = Field(description="Messages received by a worker but not yet completed")
    delayed: int = Field(description="Messages scheduled for future delivery")
    deadletter: int = Field(description="Messages that exhausted retries and moved to the DLQ")


class TranscriptionStatusResponse(BaseModel):
    """Diagnostic view of a transcription's execution across the whole pipeline."""

    transcription_id: uuid.UUID
    transcription_status: JobStatus
    title: str | None = None
    created_datetime: datetime
    updated_datetime: datetime
    error: str | None = None
    recordings: list[dict] = Field(default_factory=list, description="Recording rows and their processing status")
    stages: list[PipelineStageStatus] = Field(default_factory=list)
    queues: list[QueueDepth] = Field(default_factory=list)
    summary: str = Field(description="One-line human summary of where the pipeline is stuck or done")
