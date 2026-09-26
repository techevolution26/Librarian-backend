from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TargetType = Literal["annotation", "discussion", "reply"]
ReportReason = Literal["harassment", "hate", "spam", "privacy", "copyright", "other"]
ModerationAction = Literal["dismiss", "hide"]


class CircleModerationReportCreate(BaseModel):
    target_type: TargetType
    target_id: int = Field(gt=0)
    reason: ReportReason
    details: str | None = Field(default=None, max_length=2000)

    @field_validator("details")
    @classmethod
    def normalize_details(cls, value: str | None) -> str | None:
        return value.strip() if value is not None and value.strip() else None


class CircleModerationReportRead(BaseModel):
    id: int
    circle_id: int
    reporter_user_id: int
    target_type: TargetType
    target_id: int
    reason: ReportReason
    details: str | None
    status: str
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    action: str | None
    action_note: str | None
    created_at: datetime
    updated_at: datetime
    reporter_name: str
    reviewer_name: str | None
    target_preview: str
    target_author_name: str
    model_config = ConfigDict(from_attributes=True)


class CircleModerationReview(BaseModel):
    action: ModerationAction
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        return value.strip() if value is not None and value.strip() else None
