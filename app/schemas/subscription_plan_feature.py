from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubscriptionPlanFeatureLimitUpsert(BaseModel):
    feature_key: str = Field(min_length=2, max_length=100)
    enabled: bool = True
    limit_value: int | None = Field(default=None, ge=0, le=2_147_483_647)

    @field_validator("feature_key")
    @classmethod
    def normalize_feature_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Feature key may contain only letters, numbers, hyphens, and underscores")
        return normalized


class SubscriptionPlanFeatureLimitRead(BaseModel):
    id: int
    plan_id: int
    feature_key: str
    enabled: bool
    limit_value: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
