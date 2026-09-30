from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreatorLifetimeAccessRead(BaseModel):
    id: int
    user_id: int
    hosted_book_id: int
    purchase_id: int | None
    paid_offer_id: int | None
    status: str
    access_source: str
    granted_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime
    title: str
    author_name: str
    book_id: int

    model_config = ConfigDict(from_attributes=True)
