from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PurchaseCheckoutCreate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=255)

    @field_validator("idempotency_key")
    @classmethod
    def normalize_idempotency_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Idempotency key is required")
        return value


class PurchaseCheckoutRead(BaseModel):
    purchase_id: int
    checkout_session_id: str
    checkout_url: str


class PurchaseRead(BaseModel):
    id: int
    paid_offer_id: int
    hosted_book_id: int
    amount_minor: int
    currency: str
    provider: str
    status: str
    provider_checkout_session_id: str | None
    provider_payment_intent_id: str | None
    purchased_at: datetime | None
    refunded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
