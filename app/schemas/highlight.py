from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HighlightCreate(BaseModel):
    book_id: int
    page_number: int = Field(ge=1)
    selected_text: str = Field(min_length=1, max_length=20000)
    position: str | None = Field(default=None, max_length=10000)
    color: str = Field(default="gold", max_length=24)
    note_id: int | None = None

    @field_validator("selected_text", "color")
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        return value.strip()


class HighlightUpdate(BaseModel):
    selected_text: str | None = Field(default=None, min_length=1, max_length=20000)
    position: str | None = Field(default=None, max_length=10000)
    color: str | None = Field(default=None, max_length=24)
    note_id: int | None = None

    @field_validator("selected_text", "color")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class HighlightRead(BaseModel):
    id: int
    user_id: int
    book_id: int
    note_id: int | None = None
    page_number: int
    selected_text: str
    position: str | None = None
    color: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
