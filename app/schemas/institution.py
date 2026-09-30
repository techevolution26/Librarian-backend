from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InstitutionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Slug may contain only letters, numbers, hyphens, and underscores")
        return normalized


class InstitutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    owner_user_id: int
    status: str
    created_at: datetime
    updated_at: datetime


class InstitutionMembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    institution_id: int
    user_id: int
    role: str
    status: str
    created_at: datetime
    updated_at: datetime


class InstitutionMemberCreate(BaseModel):
    user_id: int
    role: str = "member"

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"admin", "member"}:
            raise ValueError("Institution members may have role admin or member")
        return value


class InstitutionPlanAssign(BaseModel):
    plan_id: int
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class InstitutionSubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    institution_id: int
    plan_id: int
    plan_code: str
    plan_name: str
    status: str
    starts_at: datetime
    ends_at: datetime | None
    created_at: datetime
    updated_at: datetime
