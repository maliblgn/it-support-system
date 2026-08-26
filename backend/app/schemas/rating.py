from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class TicketRatingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class TicketRatingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    user_id: int
    it_user_id: int
    it_user_name: str
    score: int
    comment: str | None
    editable_until: datetime
    created_at: datetime
    updated_at: datetime

    @field_serializer(
        "editable_until", "created_at", "updated_at", when_used="json"
    )
    def serialize_utc_datetime(self, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
