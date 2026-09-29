from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubscriptionRead(BaseModel):
    id: int
    plan_id: int
    plan_code: str
    plan_name: str
    provider: str
    provider_subscription_id: str
    status: str
    quantity: int
    current_period_start: datetime | None
    current_period_end: datetime | None
    trial_start: datetime | None
    trial_end: datetime | None
    cancel_at: datetime | None
    canceled_at: datetime | None
    ended_at: datetime | None


class CheckoutSessionCreate(BaseModel):
    plan_code: str
    idempotency_key: str


class CheckoutSessionRead(BaseModel):
    checkout_session_id: str
    checkout_url: str


class CustomerPortalRead(BaseModel):
    portal_url: str
