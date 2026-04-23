from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

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


class CircleRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    visibility: str
    avatar_url: str | None = None
    owner: CircleOwnerRead
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CircleCreate(BaseModel):
    name: str
    description: str | None = None
    visibility: str = "private"


class CircleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None


class CircleInviteCreate(BaseModel):
    user_id: int


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


class CircleProgressUpdateRead(BaseModel):
    id: int
    progress_percent: int
    current_page: int | None = None
    bookmark_page: int | None = None
    note: str | None = None
    visibility: str
    created_at: datetime
    user: CircleMemberUserRead

    model_config = ConfigDict(from_attributes=True)


class CircleProgressUpdateCreate(BaseModel):
    circle_book_id: int
    library_item_id: int
    note: str | None = None
    visibility: str = "circle"