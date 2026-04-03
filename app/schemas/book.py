from pydantic import BaseModel, ConfigDict


class BookRead(BaseModel):
    id: int
    title: str
    author: str
    cover: str
    description: str
    rating: float
    pages: int
    genre: list[str]
    source_type: str
    source_url: str | None = None
    mime_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BookContentRead(BaseModel):
    id: int
    title: str
    source_type: str
    mime_type: str | None = None
    source_url: str | None = None
    content_text: str | None = None