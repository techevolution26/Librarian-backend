from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ALLOWED_VISIBILITIES = {"draft", "published", "restricted"}


class CollectionRead(BaseModel):
    id: int
    identifier: str
    title: str
    description: str | None = None
    curator: str | None = None
    institution: str | None = None
    geographic_scope: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    subjects: list[str] = Field(default_factory=list)
    rights_statement: str | None = None
    visibility: str
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectionCreate(BaseModel):
    identifier: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    curator: str | None = None
    institution: str | None = None
    geographic_scope: str | None = None
    date_start: str | None = Field(default=None, max_length=40)
    date_end: str | None = Field(default=None, max_length=40)
    subjects: list[str] = Field(default_factory=list)
    rights_statement: str | None = Field(default=None, max_length=500)
    visibility: str = "draft"

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_VISIBILITIES:
            raise ValueError("visibility must be draft, published, or restricted")
        return normalized


class CollectionUpdate(BaseModel):
    identifier: str | None = Field(default=None, min_length=1, max_length=80)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    curator: str | None = None
    institution: str | None = None
    geographic_scope: str | None = None
    date_start: str | None = Field(default=None, max_length=40)
    date_end: str | None = Field(default=None, max_length=40)
    subjects: list[str] | None = None
    rights_statement: str | None = Field(default=None, max_length=500)
    visibility: str | None = None

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_VISIBILITIES:
            raise ValueError("visibility must be draft, published, or restricted")
        return normalized
