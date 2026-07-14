from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ResourceRead(BaseModel):
    id: int
    title: str
    author: str
    authors: list[str] = []
    cover: str
    description: str
    rating: float
    pages: int
    genre: list[str]
    tags: list[str] = []
    source_type: str
    content_type: str
    source_url: str | None = None
    mime_type: str | None = None
    visibility: str = "published"
    archived_at: datetime | None = None
    cover_path: str | None = None
    is_featured: bool = False

    model_config = ConfigDict(from_attributes=True)


class ResourceContentRead(BaseModel):
    id: int
    title: str
    source_type: str
    content_type: str
    mime_type: str | None = None
    source_url: str | None = None
    content_text: str | None = None


BookRead = ResourceRead
BookContentRead = ResourceContentRead

class AdminBookListRead(BaseModel):
    items: list[BookRead]
    total: int
    page: int
    limit: int
    pages: int