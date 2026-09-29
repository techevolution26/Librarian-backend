from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatorHostedBookRead(BaseModel):
    id: int
    submission_id: int
    creator_account_id: int
    book_id: int
    status: str
    title: str
    author_name: str
    has_access_asset: bool
    asset_id: int | None
    asset_filename: str | None
    asset_size_bytes: int | None
    asset_checksum_sha256: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreatorHostedBookListRead(BaseModel):
    items: list[CreatorHostedBookRead] = Field(default_factory=list)
    total: int = 0
