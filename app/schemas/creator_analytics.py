from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CreatorBookAnalyticsRead(BaseModel):
    hosted_book_id: int
    book_id: int
    title: str
    status: str
    reader_count: int = Field(ge=0)
    active_reader_count_30d: int = Field(ge=0)
    completed_reader_count: int = Field(ge=0)
    average_progress_percent: float = Field(ge=0, le=100)
    lifetime_owner_count: int = Field(ge=0)
    paid_offer_active: bool


class CreatorAnalyticsRead(BaseModel):
    submission_count: int = Field(ge=0)
    submitted_count: int = Field(ge=0)
    under_review_count: int = Field(ge=0)
    changes_requested_count: int = Field(ge=0)
    hosted_book_count: int = Field(ge=0)
    active_paid_offer_count: int = Field(ge=0)
    lifetime_owner_count: int = Field(ge=0)
    reader_count: int = Field(ge=0)
    active_reader_count_30d: int = Field(ge=0)
    completed_reader_count: int = Field(ge=0)
    average_progress_percent: float = Field(ge=0, le=100)
    books: list[CreatorBookAnalyticsRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
