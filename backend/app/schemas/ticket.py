from datetime import UTC, datetime
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.models.enums import TicketPriority, TicketResolutionOutcome
from app.schemas.attachment import AttachmentRead


class ItTicketView(StrEnum):
    ALL = "all"
    UNASSIGNED = "unassigned"
    MINE = "mine"
    RESOLVED = "resolved"


class TicketStatusFilter(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class AdminTicketState(StrEnum):
    ALL = "all"
    ACTIVE = "active"
    DELETED = "deleted"


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)

    @field_validator("subject", "description")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Bu alan boş bırakılamaz.")
        return normalized


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=20000)

    @field_validator("subject", "description")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Bu alan null olamaz.")
        normalized = value.strip()
        if not normalized:
            raise ValueError("Bu alan boş bırakılamaz.")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "TicketUpdate":
        if not self.model_fields_set:
            raise ValueError("En az bir değişiklik alanı gönderilmelidir.")
        return self


class TicketPriorityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: TicketPriority


class TicketResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_note: str = Field(min_length=1, max_length=20000)
    outcome: TicketResolutionOutcome = TicketResolutionOutcome.RESOLVED

    @field_validator("resolution_note")
    @classmethod
    def strip_resolution_note(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Çözüm açıklaması boş bırakılamaz.")
        return normalized


class TicketUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str
    last_name: str
    phone: str | None
    department: str


class TicketTagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    subject: str
    description: str
    department_snapshot: str
    priority: TicketPriority | None
    assigned_to: int | None
    is_resolved: bool
    resolution_outcome: TicketResolutionOutcome | None
    resolution_note: str | None
    resolved_at: datetime | None
    resolved_by: int | None
    deleted_at: datetime | None
    deleted_by: int | None
    deletion_reason: str | None
    created_at: datetime
    updated_at: datetime
    user: TicketUserRead
    attachments: list[AttachmentRead]
    tags: list[TicketTagRead] = Field(default_factory=list)

    @field_serializer(
        "created_at", "updated_at", "resolved_at", "deleted_at", when_used="json"
    )
    def serialize_utc_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ItTicketRead(TicketRead):
    assignee: TicketUserRead | None
    watchers: list[TicketUserRead] = Field(default_factory=list)


class AdminTicketRead(ItTicketRead):
    pass


class TicketPage(BaseModel):
    items: list[TicketRead]
    total: int
    page: int
    page_size: int
    pages: int


class ItTicketPage(BaseModel):
    items: list[ItTicketRead]
    total: int
    page: int
    page_size: int
    pages: int


class AdminTicketPage(BaseModel):
    items: list[AdminTicketRead]
    total: int
    page: int
    page_size: int
    pages: int


class TicketFilterAssignee(BaseModel):
    id: int
    name: str


class TicketFilterOptions(BaseModel):
    departments: list[str]
    assignees: list[TicketFilterAssignee]
    tags: list[TicketTagRead]


class TicketHistoryRead(BaseModel):
    id: int
    action: str
    actor_user_id: int | None
    actor_name: str | None
    details: dict[str, object]
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_history_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
