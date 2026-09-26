from datetime import datetime

from pydantic import BaseModel, Field


class CircleInvitationCreate(BaseModel):
    expires_in_days: int = Field(default=7, ge=1, le=30)
    max_uses: int = Field(default=1, ge=1, le=100)


class CircleInvitationCreateRead(BaseModel):
    id: int
    invitation_type: str
    token: str
    invite_url: str
    expires_at: datetime
    max_uses: int
    uses: int
    status: str


class CircleInvitationPreviewRead(BaseModel):
    id: int
    invitation_type: str
    circle_id: int
    circle_name: str
    circle_slug: str
    circle_description: str | None = None
    circle_visibility: str
    circle_icon_key: str
    member_count: int
    inviter_id: int
    inviter_name: str
    expires_at: datetime
    max_uses: int
    uses: int
    status: str
    can_accept: bool


class CircleInvitationAcceptRead(BaseModel):
    invitation_id: int
    circle_id: int
    circle_name: str
    membership_id: int
    status: str


class CircleInvitationRead(BaseModel):
    id: int
    invitation_type: str
    circle_id: int
    circle_name: str
    created_by_user_id: int
    expires_at: datetime
    max_uses: int
    uses: int
    status: str
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    created_at: datetime


class CircleInvitationRevokeRead(BaseModel):
    id: int
    status: str
    revoked_at: datetime
