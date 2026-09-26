from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ArchivalCanvasRead(BaseModel):
    id: int
    archival_object_id: int
    asset_id: int | None = None
    canvas_identifier: str
    sequence: int
    page_number: int | None = None
    label: str
    media_type: str | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArchivalCanvasCreate(BaseModel):
    asset_id: int | None = None
    sequence: int = Field(gt=0)
    page_number: int | None = Field(default=None, gt=0)
    label: str = Field(min_length=1, max_length=255)
    media_type: str | None = Field(default=None, max_length=100)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    duration_seconds: float | None = Field(default=None, ge=0)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("label cannot be empty")
        return normalized


class ArchivalCanvasUpdate(BaseModel):
    asset_id: int | None = None
    sequence: int | None = Field(default=None, gt=0)
    page_number: int | None = Field(default=None, gt=0)
    label: str | None = Field(default=None, min_length=1, max_length=255)
    media_type: str | None = Field(default=None, max_length=100)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    duration_seconds: float | None = Field(default=None, ge=0)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("label cannot be empty")
        return normalized
