from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    id: int
    type: str
    title: str
    body: str
    data: dict | None = None
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadCountRead(BaseModel):
    unread: int
