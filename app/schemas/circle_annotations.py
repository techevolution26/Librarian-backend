from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CircleAnnotationCreate(BaseModel):
    circle_book_id: int
    page_number: int = Field(ge=1)
    selected_text: str | None = Field(default=None, max_length=20000)
    position: str | None = Field(default=None, max_length=10000)
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("selected_text", "position", "body")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class CircleAnnotationUpdate(BaseModel):
    page_number: int | None = Field(default=None, ge=1)
    selected_text: str | None = Field(default=None, max_length=20000)
    position: str | None = Field(default=None, max_length=10000)
    body: str | None = Field(default=None, min_length=1, max_length=10000)

    @field_validator("selected_text", "position", "body")
    @classmethod
    def normalize_strings(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class CircleAnnotationUserRead(BaseModel):
    id: int
    full_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CircleAnnotationRead(BaseModel):
    id: int
    circle_id: int
    circle_book_id: int
    book_id: int
    user_id: int
    page_number: int
    selected_text: str | None = None
    position: str | None = None
    body: str
    visibility: str
    created_at: datetime
    updated_at: datetime
    user: CircleAnnotationUserRead

    model_config = ConfigDict(from_attributes=True)
