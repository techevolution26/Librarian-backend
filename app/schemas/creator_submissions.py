from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatorBookSubmissionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author_name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=20000)
    language: str = Field(default="en", min_length=2, max_length=40)
    genres: list[str] = Field(default_factory=list, max_length=30)
    creator_note: str | None = Field(default=None, max_length=5000)


class CreatorBookSubmissionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=20000)
    language: str | None = Field(default=None, min_length=2, max_length=40)
    genres: list[str] | None = Field(default=None, max_length=30)
    creator_note: str | None = Field(default=None, max_length=5000)


class CreatorBookSubmissionRead(BaseModel):
    id: int
    creator_account_id: int
    title: str
    author_name: str
    description: str
    language: str
    genres: list[str]
    creator_note: str | None
    status: str
    review_note: str | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewed_by_user_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreatorBookSubmissionListRead(BaseModel):
    items: list[CreatorBookSubmissionRead]
    total: int


class CreatorSubmissionReviewUpdate(BaseModel):
    status: str = Field(pattern=r"^(under_review|changes_requested)$")
    review_note: str | None = Field(default=None, max_length=5000)
