from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookmarkCreate(BaseModel):
    book_id: int
    page_number: int | None = Field(default=None, ge=1)
    position: str | None = Field(default=None, max_length=255)
    title: str = Field(default="Bookmark", min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=10000)
    color: str | None = Field(default=None, max_length=32)

    @field_validator("title", "position", "note", "color")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BookmarkUpdate(BaseModel):
    page_number: int | None = Field(default=None, ge=1)
    position: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=10000)
    color: str | None = Field(default=None, max_length=32)

    @field_validator("title", "position", "note", "color")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BookmarkRead(BaseModel):
    id: int
    user_id: int
    book_id: int
    page_number: int | None = None
    position: str | None = None
    title: str
    note: str | None = None
    color: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
