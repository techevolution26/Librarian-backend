from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConnectionUserRead(BaseModel):
    id: int
    full_name: str
    email: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserConnectionRead(BaseModel):
    id: int
    status: str
    relationship_type: str
    created_at: datetime
    requester: ConnectionUserRead
    addressee: ConnectionUserRead


class UserConnectionCreate(BaseModel):
    email: str
    relationship_type: str = "friend"


class UserConnectionAction(BaseModel):
    action: str  # accept | decline | block