from datetime import UTC, datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.core.security import normalize_email
from app.schemas.user import UserRead


class AdminItUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    temporary_password: str = Field(min_length=12, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    department: str = Field(default="Bilgi İşlem", min_length=1, max_length=150)

    @field_validator("email")
    @classmethod
    def normalize_email_value(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("first_name", "last_name", "department")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Bu alan boş bırakılamaz.")
        return normalized

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    department: str | None = Field(default=None, min_length=1, max_length=150)

    @field_validator("first_name", "last_name", "department")
    @classmethod
    def strip_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Bu alan null olamaz.")
        normalized = value.strip()
        if not normalized:
            raise ValueError("Bu alan boş bırakılamaz.")
        return normalized

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def require_change(self) -> "AdminUserUpdate":
        if not self.model_fields_set:
            raise ValueError("En az bir değişiklik alanı gönderilmelidir.")
        return self


class AdminUserStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("İşlem nedeni en az 3 karakter olmalıdır.")
        return normalized


class AdminTemporaryPasswordReset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temporary_password: str = Field(min_length=12, max_length=128)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("İşlem nedeni en az 3 karakter olmalıdır.")
        return normalized


class AdminUserDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_email: str = Field(min_length=3, max_length=320)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("confirmation_email")
    @classmethod
    def normalize_confirmation_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Silme nedeni en az 3 karakter olmalıdır.")
        return normalized


class AdminUserPage(BaseModel):
    items: list[UserRead]
    total: int
    page: int
    page_size: int
    pages: int


class AdminDashboardRead(BaseModel):
    total_users: int
    active_users: int
    it_users: int
    open_tickets: int
    deleted_tickets: int
    unrated_resolved_tickets: int


class TicketDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Silme nedeni en az 3 karakter olmalıdır.")
        return normalized


class AdminTicketAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    it_user_id: int = Field(gt=0)


class AuditEventRead(BaseModel):
    id: int
    actor_user_id: int | None
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: int | None
    details: dict[str, object]
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_utc_datetime(self, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class AuditEventPage(BaseModel):
    items: list[AuditEventRead]
    total: int
    page: int
    page_size: int
    pages: int
