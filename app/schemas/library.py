from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.book import BookRead

LibraryStatus = Literal["reading", "saved", "finished"]


class LibraryItemRead(BaseModel):
    id: int
    status: LibraryStatus
    progress: int
    current_page: int | None = None
    total_pages: int | None = None
    bookmark_page: int | None = None
    last_read_at: datetime | None = None
    saved_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime | None = None
    book: BookRead

    model_config = ConfigDict(from_attributes=True)


class LibraryMutationCreate(BaseModel):
    book_id: int
    status: LibraryStatus = "saved"


class StartReadingPayload(BaseModel):
    book_id: int


class PdfProgressUpdate(BaseModel):
    current_page: int
    total_pages: int
    progress: int
    bookmark_page: int | None = None


class LibrarySummary(BaseModel):
    all: int
    reading: int
    saved: int
    finished: int
    average_rating: float


class SelectableLibraryBookRead(BaseModel):
    id: int
    status: str
    progress: int
    current_page: int | None = None
    bookmark_page: int | None = None
    book: BookRead

    model_config = ConfigDict(from_attributes=True)