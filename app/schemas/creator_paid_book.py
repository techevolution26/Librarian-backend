from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreatorPaidBookCreate(BaseModel):
    price_amount_minor: int = Field(gt=0, le=2_147_483_647)
    currency: str = Field(min_length=3, max_length=3)
    status: str = "draft"

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter ISO-style code")
        return normalized

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"draft", "active"}:
            raise ValueError("Status must be draft or active")
        return value


class CreatorPaidBookUpdate(BaseModel):
    price_amount_minor: int | None = Field(default=None, gt=0, le=2_147_483_647)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: str | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter ISO-style code")
        return normalized

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in {"draft", "active", "archived"}:
            raise ValueError("Status must be draft, active, or archived")
        return value


class CreatorPaidBookRead(BaseModel):
    id: int
    hosted_book_id: int
    creator_account_id: int
    price_amount_minor: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
