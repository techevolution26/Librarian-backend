from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ArchivalProvenanceBase(BaseModel):
    source_institution: str | None = Field(default=None, max_length=255)
    source_collection: str | None = Field(default=None, max_length=255)
    shelfmark: str | None = Field(default=None, max_length=255)
    accession_number: str | None = Field(default=None, max_length=100)
    original_format: str | None = Field(default=None, max_length=100)
    physical_condition: str | None = None
    origin_place: str | None = Field(default=None, max_length=255)
    origin_date: date | None = None
    digitized_by: str | None = Field(default=None, max_length=255)
    digitized_at: datetime | None = None
    digitization_method: str | None = Field(default=None, max_length=255)
    scanner_device: str | None = Field(default=None, max_length=255)
    master_format: str | None = Field(default=None, max_length=100)
    derivative_format: str | None = Field(default=None, max_length=100)
    software: str | None = Field(default=None, max_length=255)
    notes: str | None = None

    @field_validator(
        "source_institution",
        "source_collection",
        "shelfmark",
        "accession_number",
        "original_format",
        "origin_place",
        "digitized_by",
        "digitization_method",
        "scanner_device",
        "master_format",
        "derivative_format",
        "software",
    )
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class ArchivalProvenanceRead(ArchivalProvenanceBase):
    id: int
    archival_object_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArchivalProvenanceUpdate(ArchivalProvenanceBase):
    pass
