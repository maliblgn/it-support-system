from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    uploaded_by: int
    original_file_name: str
    content_type: str
    file_extension: str
    file_size_bytes: int
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_utc_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
