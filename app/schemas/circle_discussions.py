from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CircleDiscussionCreate(BaseModel):
    circle_book_id: int
    page_number: int | None = Field(default=None, ge=1)
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        return value.strip()


class CircleDiscussionUpdate(BaseModel):
    page_number: int | None = Field(default=None, ge=1)
    body: str | None = Field(default=None, min_length=1, max_length=10000)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class CircleDiscussionReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        return value.strip()


class CircleDiscussionReplyUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        return value.strip()


class CircleDiscussionUserRead(BaseModel):
    id: int
    full_name: str
    avatar_url: str | None = None
    model_config = ConfigDict(from_attributes=True)


class CircleDiscussionReplyRead(BaseModel):
    id: int
    discussion_id: int
    circle_id: int
    user_id: int
    body: str
    created_at: datetime
    updated_at: datetime
    user: CircleDiscussionUserRead
    model_config = ConfigDict(from_attributes=True)


class CircleDiscussionRead(BaseModel):
    id: int
    circle_id: int
    circle_book_id: int
    book_id: int
    user_id: int
    page_number: int | None = None
    body: str
    created_at: datetime
    updated_at: datetime
    replies_count: int = 0
    user: CircleDiscussionUserRead
    model_config = ConfigDict(from_attributes=True)


class CircleDiscussionDetailRead(CircleDiscussionRead):
    replies: list[CircleDiscussionReplyRead] = Field(default_factory=list)
