from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_list(value: list[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class ArchivalMetadataBase(BaseModel):
    alternative_titles: list[str] = Field(default_factory=list)
    contributors: list[str] = Field(default_factory=list)
    language: str | None = Field(default=None, max_length=40)
    subjects: list[str] = Field(default_factory=list)
    genre: list[str] = Field(default_factory=list)
    publication_date: date | None = None
    publisher: str | None = Field(default=None, max_length=255)
    edition: str | None = Field(default=None, max_length=255)
    external_identifier: str | None = Field(default=None, max_length=255)
    notes: str | None = None

    @field_validator("alternative_titles", "contributors", "subjects", "genre")
    @classmethod
    def normalize_lists(cls, value: list[str]) -> list[str]:
        return _clean_list(value)

    @field_validator("language", "publisher", "edition", "external_identifier")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class ArchivalMetadataRead(ArchivalMetadataBase):
    id: int
    archival_object_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArchivalMetadataUpdate(ArchivalMetadataBase):
    pass
