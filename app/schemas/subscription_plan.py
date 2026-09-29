from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.subscription_plan_feature import SubscriptionPlanFeatureLimitRead


class SubscriptionPlanCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    price_amount_minor: int = Field(default=0, ge=0, le=2_147_483_647)
    currency: str = Field(default="usd", min_length=3, max_length=3)
    billing_interval: str = "none"
    status: str = "draft"
    sort_order: int = Field(default=0, ge=0, le=2_147_483_647)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Plan code may contain only letters, numbers, hyphens, and underscores")
        return normalized

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter ISO-style code")
        return normalized

    @field_validator("billing_interval")
    @classmethod
    def validate_interval(cls, value: str) -> str:
        if value not in {"none", "month", "year"}:
            raise ValueError("Billing interval must be none, month, or year")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"draft", "active", "archived"}:
            raise ValueError("Status must be draft, active, or archived")
        return value


class SubscriptionPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    price_amount_minor: int | None = Field(default=None, ge=0, le=2_147_483_647)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    billing_interval: str | None = None
    status: str | None = None
    sort_order: int | None = Field(default=None, ge=0, le=2_147_483_647)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter ISO-style code")
        return normalized

    @field_validator("billing_interval")
    @classmethod
    def validate_interval(cls, value: str | None) -> str | None:
        if value is not None and value not in {"none", "month", "year"}:
            raise ValueError("Billing interval must be none, month, or year")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in {"draft", "active", "archived"}:
            raise ValueError("Status must be draft, active, or archived")
        return value


class SubscriptionPlanRead(BaseModel):
    id: int
    code: str
    name: str
    description: str
    price_amount_minor: int
    currency: str
    billing_interval: str
    status: str
    sort_order: int
    created_at: datetime
    updated_at: datetime
    feature_limits: list[SubscriptionPlanFeatureLimitRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
