from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.book import BookRead


class ProfileStat(BaseModel):
    label: str
    value: str


class ReadingProgressItem(BaseModel):
    id: int
    title: str
    progress: int


class ActivityItem(BaseModel):
    id: int
    title: str
    action: str
    href: str


class UserProfileRead(BaseModel):
    name: str
    email: str
    plan: str
    avatar: str | None = None
    member_since: str
    library_status: str
    reading_mode: str
    preferences: list[str]
    stats: list[ProfileStat]
    favorite_books: list[BookRead]
    recent_books: list[BookRead]
    reading_progress: list[ReadingProgressItem]
    suggested_book: BookRead | None = None
    recent_activity: list[ActivityItem]


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None

    model_config = ConfigDict(extra="forbid")


class SidebarSummaryRead(BaseModel):
    full_name: str
    avatar_url: str | None = None
    reading_streak_days: int