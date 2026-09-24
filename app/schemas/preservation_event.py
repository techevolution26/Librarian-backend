from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.preservation_event import (
    PRESERVATION_EVENT_OUTCOMES,
    PRESERVATION_EVENT_TYPES,
)


class PreservationEventCreate(BaseModel):
    asset_id: int | None = None
    event_type: str
    event_date: datetime | None = None
    outcome: str = "unknown"
    agent: str | None = None
    detail: str | None = None
    source_storage_key: str | None = None
    target_storage_key: str | None = None
    checksum: str | None = None
    checksum_algorithm: str | None = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in PRESERVATION_EVENT_TYPES:
            raise ValueError("Unsupported preservation event type")
        return value

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in PRESERVATION_EVENT_OUTCOMES:
            raise ValueError("Unsupported preservation event outcome")
        return value

    @field_validator(
        "agent",
        "detail",
        "source_storage_key",
        "target_storage_key",
        "checksum",
        "checksum_algorithm",
        mode="before",
    )
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class PreservationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    archival_object_id: int
    asset_id: int | None
    event_type: str
    event_date: datetime
    outcome: str
    agent: str | None
    detail: str | None
    source_storage_key: str | None
    target_storage_key: str | None
    checksum: str | None
    checksum_algorithm: str | None
    created_at: datetime
