from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.book import BookRead


class CircleOwnerRead(BaseModel):
    id: int
    full_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CircleMemberUserRead(BaseModel):
    id: int
    full_name: str
    email: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CircleMemberRead(BaseModel):
    id: int
    role: str
    status: str
    joined_at: datetime | None = None
    user: CircleMemberUserRead

    model_config = ConfigDict(from_attributes=True)


class CircleJoinConditions(BaseModel):
    require_approval: bool = False
    require_rules_acceptance: bool = True
    questions: list[str] = Field(default_factory=list)


class CircleRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    visibility: str
    join_policy: str
    join_conditions: CircleJoinConditions
    avatar_url: str | None = None
    owner: CircleOwnerRead
    is_member: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CircleCreate(BaseModel):
    name: str
    description: str | None = None
    visibility: str = "private"
    join_policy: str = "invite_only"
    join_conditions: CircleJoinConditions = Field(default_factory=CircleJoinConditions)


class CircleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None
    join_policy: str | None = None
    join_conditions: CircleJoinConditions | None = None


class CircleInviteCreate(BaseModel):
    user_id: int


class CirclePublicRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    visibility: str
    join_policy: str
    join_conditions: CircleJoinConditions
    avatar_url: str | None = None
    owner: CircleOwnerRead
    member_count: int
    book_count: int
    created_at: datetime


class CircleJoinRequestCreate(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


class CircleJoinRequestRead(BaseModel):
    id: int
    circle_id: int
    user_id: int
    status: str
    answers: dict[str, str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CircleBookRead(BaseModel):
    id: int
    title_override: str | None = None
    description: str | None = None
    start_date: date | None = None
    target_end_date: date | None = None
    status: str
    book: BookRead

    model_config = ConfigDict(from_attributes=True)


class CircleBookCreate(BaseModel):
    book_id: int
    title_override: str | None = None
    description: str | None = None
    start_date: date | None = None
    target_end_date: date | None = None


class CircleProgressBookRead(BaseModel):
    id: int
    title: str

    model_config = ConfigDict(from_attributes=True)


class CircleProgressCircleBookRead(BaseModel):
    id: int
    book: CircleProgressBookRead

    model_config = ConfigDict(from_attributes=True)


class CircleProgressUpdateRead(BaseModel):
    id: int
    progress_percent: int
    current_page: int | None = None
    bookmark_page: int | None = None
    note: str | None = None
    visibility: str
    created_at: datetime
    user: CircleMemberUserRead
    circle_book: CircleProgressCircleBookRead | None = None

    model_config = ConfigDict(from_attributes=True)


class CircleProgressUpdateCreate(BaseModel):
    circle_book_id: int
    library_item_id: int
    note: str | None = None
    visibility: str = "circle"