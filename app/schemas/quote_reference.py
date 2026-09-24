from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuoteReferenceCreate(BaseModel):
    book_id: int
    highlight_id: int | None = None
    note_id: int | None = None
    page_number: int | None = Field(default=None, ge=1)
    locator: str | None = Field(default=None, max_length=10000)
    quote_text: str = Field(min_length=1, max_length=20000)

    @field_validator("locator", "quote_text")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class QuoteReferenceUpdate(BaseModel):
    note_id: int | None = None
    page_number: int | None = Field(default=None, ge=1)
    locator: str | None = Field(default=None, max_length=10000)
    quote_text: str | None = Field(default=None, min_length=1, max_length=20000)

    @field_validator("locator", "quote_text")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class QuoteReferenceRead(BaseModel):
    id: int
    user_id: int
    book_id: int
    highlight_id: int | None = None
    note_id: int | None = None
    page_number: int | None = None
    locator: str | None = None
    quote_text: str
    citation: str
    source_title: str
    source_author: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
