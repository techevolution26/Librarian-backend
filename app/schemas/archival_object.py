from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.archival_object import (
    ARCHIVAL_OBJECT_TYPES,
    ARCHIVAL_OBJECT_VISIBILITIES,
)
from app.schemas.archival_metadata import ArchivalMetadataRead, ArchivalMetadataUpdate
from app.schemas.archival_provenance import (
    ArchivalProvenanceRead,
    ArchivalProvenanceUpdate,
)


class ArchivalObjectRead(BaseModel):
    id: int
    identifier: str
    object_type: str
    title: str
    description: str | None = None
    collection_id: int | None = None
    visibility: str
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    book_id: int | None = None
    metadata: ArchivalMetadataRead | None = None
    provenance: ArchivalProvenanceRead | None = None

    model_config = ConfigDict(from_attributes=True)


class ArchivalObjectCreate(BaseModel):
    identifier: str = Field(min_length=1, max_length=100)
    object_type: str = "other"
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    collection_id: int | None = None
    visibility: str = "draft"
    metadata: ArchivalMetadataUpdate | None = None
    provenance: ArchivalProvenanceUpdate | None = None

    @field_validator("object_type")
    @classmethod
    def validate_object_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ARCHIVAL_OBJECT_TYPES:
            raise ValueError("unsupported archival object type")
        return normalized

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ARCHIVAL_OBJECT_VISIBILITIES:
            raise ValueError("visibility must be draft, published, or restricted")
        return normalized


class ArchivalObjectUpdate(BaseModel):
    identifier: str | None = Field(default=None, min_length=1, max_length=100)
    object_type: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    collection_id: int | None = None
    visibility: str | None = None
    metadata: ArchivalMetadataUpdate | None = None
    provenance: ArchivalProvenanceUpdate | None = None

    @field_validator("object_type")
    @classmethod
    def validate_object_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in ARCHIVAL_OBJECT_TYPES:
            raise ValueError("unsupported archival object type")
        return normalized

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in ARCHIVAL_OBJECT_VISIBILITIES:
            raise ValueError("visibility must be draft, published, or restricted")
        return normalized
