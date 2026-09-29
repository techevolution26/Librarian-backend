from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EntitlementRead(BaseModel):
    id: int
    entitlement_type: str
    book_id: int | None
    feature_key: str | None
    source: str
    source_reference: str
    status: str
    starts_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookAccessDecision(BaseModel):
    allowed: bool
    reason: str
    entitlement_id: int | None = None
    source: str | None = None
    expires_at: datetime | None = None
