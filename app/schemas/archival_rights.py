from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ArchivalRightsBase(BaseModel):
    rights_holder: str | None = Field(default=None, max_length=255)
    rights_statement: str | None = None
    license: str | None = Field(default=None, max_length=255)
    copyright_status: str | None = Field(default=None, max_length=40)
    jurisdiction: str | None = Field(default=None, max_length=120)
    rights_source: str | None = Field(default=None, max_length=500)
    access_conditions: str | None = None
    reproduction_conditions: str | None = None
    attribution: str | None = None
    view_allowed: bool | None = None
    download_allowed: bool | None = None
    redistribution_allowed: bool | None = None
    commercial_use_allowed: bool | None = None
    verified_at: datetime | None = None
    verified_by: str | None = Field(default=None, max_length=255)
    notes: str | None = None

    @field_validator(
        "rights_holder",
        "license",
        "copyright_status",
        "jurisdiction",
        "rights_source",
        "verified_by",
    )
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class ArchivalRightsRead(ArchivalRightsBase):
    id: int
    archival_object_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArchivalRightsUpdate(ArchivalRightsBase):
    pass
