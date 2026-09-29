from pydantic import BaseModel, ConfigDict


class BillingStatusRead(BaseModel):
    provider: str
    configured: bool
    has_customer: bool
    has_subscription: bool
    effective_plan_code: str | None

    model_config = ConfigDict(from_attributes=True)
