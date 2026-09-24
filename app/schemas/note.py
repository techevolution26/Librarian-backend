from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteCreate(BaseModel):
    book_id: int | None = None
    bookmark_id: int | None = None
    page_number: int | None = Field(default=None, ge=1)
    title: str = Field(default="Untitled note", min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=50000)

    @field_validator("title", "body")
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        return value.strip()


class NoteUpdate(BaseModel):
    book_id: int | None = None
    bookmark_id: int | None = None
    page_number: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    body: str | None = Field(default=None, min_length=1, max_length=50000)

    @field_validator("title", "body")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class NoteRead(BaseModel):
    id: int
    notebook_id: int
    book_id: int | None = None
    bookmark_id: int | None = None
    page_number: int | None = None
    title: str
    body: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
