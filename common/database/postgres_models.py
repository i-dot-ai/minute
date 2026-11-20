from datetime import datetime
from enum import StrEnum, auto
from typing import TypedDict
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, Column, Index, UniqueConstraint, text
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
    return Column(TIMESTAMP(timezone=True), nullable=False, server_default=now(), default=None, onupdate=now())


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


class Permission(StrEnum):
    """The full set of granular capabilities in the system.

    Own-scoped capabilities (``*.own``) are evaluated against the resource's
    creator; ``*.any`` capabilities grant the action over any resource in the
    context (an org) regardless of creator.
    """

    FILE_CREATE = "file.create"
    FILE_READ_OWN = "file.read.own"
    FILE_EDIT_OWN = "file.edit.own"
    FILE_DELETE_OWN = "file.delete.own"
    FILE_EXPORT_OWN = "file.export.own"
    FILE_READ_ANY = "file.read.any"
    FILE_OPEN_ANY = "file.open.any"
    MEMBERSHIP_MANAGE = "membership.manage"


class MinuteVersion(BaseTableMixin, table=True):
    __tablename__ = "minute_version"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    minute_id: UUID = Field(foreign_key="minute.id", ondelete="CASCADE")
    minute: Mapped["Minute"] = Relationship(back_populates="minute_versions")
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


# Main models with table=True for DB tables
class User(BaseTableMixin, table=True):
    __tablename__ = "user"
    # Case-insensitive uniqueness on email — emails are stored lowercased
    # (see backend/api/dependencies/get_current_user.py), but this guards
    # against accidental case-variant duplicates regardless.
    __table_args__ = (Index("ix_user_email_lower", text("lower(email)"), unique=True),)
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    email: str = Field(index=True)
    display_name: str | None = Field(default=None)
    data_retention_days: int | None = Field(default=30, sa_column_kwargs={"server_default": "30"})
    # The user's chosen default template. At most one is ever set: a custom template
    # (default_template_id) or a system template keyed by name (default_template_name).
    # Both null means no explicit default (falls back to the implicit General template).
    default_template_id: UUID | None = Field(default=None, foreign_key="user_template.id", ondelete="SET NULL")
    default_template_name: str | None = Field(default=None)
    transcriptions: list["Transcription"] = Relationship(back_populates="user")


class Recording(BaseTableMixin, table=True):
    __tablename__ = "recording"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    user_id: UUID = Field(foreign_key="user.id", nullable=False)
    org_id: UUID | None = Field(default=None, foreign_key="organisation.id", ondelete="SET NULL")
    s3_file_key: str
    transcription_id: UUID | None = Field(default=None, foreign_key="transcription.id", ondelete="SET NULL")
    transcription: "Transcription" = Relationship(back_populates="recordings")


class Transcription(BaseTableMixin, table=True):
    __tablename__ = "transcription"
    __table_args__ = (
        Index("ix_transcription_title_trgm", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
    )
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
    org_id: UUID | None = Field(default=None, foreign_key="organisation.id", ondelete="SET NULL")
    minutes: list[Minute] = Relationship(
        back_populates="transcription",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": col(Minute.created_datetime).desc()},
    )
    recordings: Mapped[list[Recording]] = Relationship(
        back_populates="transcription",
        sa_relationship_kwargs={"order_by": col(Recording.created_datetime).desc()},
    )

    @property
    def no_speech_detected(self) -> bool:
        """Whether transcription completed without any speech transcribed."""
        return self.status == JobStatus.COMPLETED and not self.dialogue_entries


class TemplateType(StrEnum):
    DOCUMENT = auto()
    FORM = auto()


class TemplateQuestion(BaseTableMixin, table=True):
    __tablename__ = "template_question"

    position: int
    title: str
    description: str

    user_template_id: UUID = Field(foreign_key="user_template.id", ondelete="CASCADE")
    user_template: "UserTemplate" = Relationship(back_populates="questions")


class UserTemplate(BaseTableMixin, table=True):
    __tablename__ = "user_template"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)

    name: str
    content: str
    description: str = ""

    type: TemplateType = Field(
        default=TemplateType.DOCUMENT, sa_column_kwargs={"server_default": TemplateType.DOCUMENT.name}
    )

    user_id: UUID | None = Field(default=None, foreign_key="user.id")

    minutes: list[Minute] = Relationship(back_populates="user_template")

    questions: list[TemplateQuestion] = Relationship(
        back_populates="user_template",
        passive_deletes="all",
        sa_relationship_kwargs={"order_by": TemplateQuestion.position},
    )


# ---------------------------------------------------------------------------
# Authorization: organisations, membership, roles and permissions
# ---------------------------------------------------------------------------


class Organisation(BaseTableMixin, table=True):
    __tablename__ = "organisation"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    name: str

    memberships: list["Membership"] = Relationship(back_populates="organisation")


class Membership(BaseTableMixin, table=True):
    __tablename__ = "membership"
    __table_args__ = (UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),)
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    user_id: UUID = Field(foreign_key="user.id", ondelete="CASCADE", index=True)
    org_id: UUID = Field(foreign_key="organisation.id", ondelete="CASCADE", index=True)
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": text("true")})

    organisation: Organisation = Relationship(back_populates="memberships")
    membership_roles: list["MembershipRole"] = Relationship(
        back_populates="membership",
        cascade_delete=True,
    )


class RolePermission(BaseTableMixin, table=True):
    __tablename__ = "role_permission"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)
    role_id: UUID = Field(foreign_key="role.id", ondelete="CASCADE", index=True)
    permission_id: UUID = Field(foreign_key="permission.id", ondelete="CASCADE", index=True)


class Role(BaseTableMixin, table=True):
    __tablename__ = "role"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    name: str = Field(index=True, unique=True)
    is_system: bool = Field(default=True, sa_column_kwargs={"server_default": text("true")})

    role_permissions: list[RolePermission] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class PermissionRecord(BaseTableMixin, table=True):
    __tablename__ = "permission"
    created_datetime: datetime = Field(sa_column=created_datetime_column(), default=None)
    updated_datetime: datetime = Field(sa_column=updated_datetime_column(), default=None)
    name: str = Field(index=True, unique=True)


class MembershipRole(BaseTableMixin, table=True):
    __tablename__ = "membership_role"
    __table_args__ = (UniqueConstraint("membership_id", "role_id", name="uq_membership_role"),)
    membership_id: UUID = Field(foreign_key="membership.id", ondelete="CASCADE", index=True)
    role_id: UUID = Field(foreign_key="role.id", ondelete="CASCADE", index=True)

    membership: Membership = Relationship(back_populates="membership_roles")
    role: Role = Relationship()
