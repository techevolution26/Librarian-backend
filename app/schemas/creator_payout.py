from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreatorPayoutRequest(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    amount_minor: int = Field(gt=0, le=2_147_483_647)
    idempotency_key: str = Field(min_length=8, max_length=255)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter ISO-style code")
        return normalized

    @field_validator("idempotency_key", mode="before")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 8:
            raise ValueError("Idempotency key must contain at least 8 characters")
        return normalized


class CreatorPayoutFailure(BaseModel):
    failure_code: str = Field(min_length=1, max_length=80)
    failure_message: str = Field(min_length=1, max_length=500)


class CreatorPayoutProviderUpdate(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    provider_payout_id: str | None = Field(default=None, max_length=255)
    provider_reference: str | None = Field(default=None, max_length=255)


class CreatorPayoutRead(BaseModel):
    id: int
    creator_account_id: int
    currency: str
    requested_amount_minor: int
    eligible_amount_minor: int
    status: str
    provider: str | None
    provider_payout_id: str | None
    provider_reference: str | None
    provider_idempotency_key: str
    idempotency_key: str
    failure_code: str | None
    failure_message: str | None
    attempt_count: int
    requested_at: datetime
    approved_at: datetime | None
    processing_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreatorPayoutBalance(BaseModel):
    currency: str
    ledger_creator_share_minor: int
    allocated_active_minor: int
    eligible_balance_minor: int


class CreatorPayoutOverview(BaseModel):
    balances: list[CreatorPayoutBalance]
    payouts: list[CreatorPayoutRead]
