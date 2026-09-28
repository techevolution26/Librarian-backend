from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreatorRevenueRecordCreate(BaseModel):
    paid_offer_id: int = Field(gt=0)
    buyer_user_id: int | None = Field(default=None, gt=0)
    entry_type: str = "sale"
    gross_amount_minor: int = Field(gt=0, le=2_147_483_647)
    creator_share_minor: int = Field(ge=0, le=2_147_483_647)
    platform_share_minor: int = Field(ge=0, le=2_147_483_647)
    currency: str = Field(min_length=3, max_length=3)
    provider: str = Field(min_length=1, max_length=40)
    provider_event_id: str = Field(min_length=1, max_length=255)
    provider_reference: str | None = Field(default=None, max_length=255)
    occurred_at: datetime

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter ISO-style code")
        return normalized

    @field_validator("provider", "provider_event_id", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized

    @field_validator("entry_type")
    @classmethod
    def validate_entry_type(cls, value: str) -> str:
        if value not in {"sale", "reversal", "adjustment"}:
            raise ValueError("Entry type must be sale, reversal, or adjustment")
        return value


class CreatorRevenueLedgerEntryRead(BaseModel):
    id: int
    creator_account_id: int
    hosted_book_id: int
    paid_offer_id: int
    buyer_user_id: int | None
    entry_type: str
    gross_amount_minor: int
    creator_share_minor: int
    platform_share_minor: int
    currency: str
    provider: str
    provider_event_id: str
    provider_reference: str | None
    occurred_at: datetime
    recorded_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreatorRevenueSummary(BaseModel):
    entry_count: int = Field(ge=0)
    gross_amount_minor: int = Field(ge=0)
    creator_share_minor: int = Field(ge=0)
    platform_share_minor: int = Field(ge=0)
    currencies: list[str] = Field(default_factory=list)
    entries: list[CreatorRevenueLedgerEntryRead] = Field(default_factory=list)
