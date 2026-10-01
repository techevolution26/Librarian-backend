from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CreatorAccountCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    bio: str | None = Field(default=None, max_length=2000)
    website_url: HttpUrl | None = None
    profile_image_url: HttpUrl | None = None
    is_public: bool = True


class CreatorAccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=3, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    bio: str | None = Field(default=None, max_length=2000)
    website_url: HttpUrl | None = None
    profile_image_url: HttpUrl | None = None
    is_public: bool | None = None


class CreatorAccountRead(BaseModel):
    id: int
    user_id: int
    display_name: str
    slug: str
    bio: str | None
    website_url: str | None
    profile_image_url: str | None
    status: str
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreatorDashboardRead(BaseModel):
    account: CreatorAccountRead
    profile_completion_percent: int
    profile_complete: bool
    missing_profile_fields: list[str] = Field(default_factory=list)


class CreatorPublicBookRead(BaseModel):
    id: int
    title: str
    author: str
    cover: str
    description: str
    pages: int
    genre: list[str] = Field(default_factory=list)
    paid_offer_id: int | None = None
    price_amount_minor: int | None = None
    currency: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CreatorPublicProfileRead(BaseModel):
    display_name: str
    slug: str
    bio: str | None
    website_url: str | None
    profile_image_url: str | None
    books: list[CreatorPublicBookRead] = Field(default_factory=list)
