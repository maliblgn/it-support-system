from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.models.enums import EmailStatus, NotificationType


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int | None
    type: NotificationType
    title: str
    message: str
    is_read: bool
    read_at: datetime | None
    email_status: EmailStatus
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at", "read_at", when_used="json")
    def serialize_utc_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class NotificationPage(BaseModel):
    items: list[NotificationRead]
    total: int
    page: int
    page_size: int
    pages: int
