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

    # Archival / provenance metadata
    accession_no: str | None = None
    language: str = "en"
    subjects: list[str] = []
    origin: str | None = None
    era: str | None = None
    original_format: str = "born-digital"
    rights_statement: str = "all-rights-reserved"
    condition_notes: str | None = None
    curator_note: str | None = None
    checksum_sha256: str | None = None
    digitized_by: str | None = None
    digitized_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BookFacets(BaseModel):
    """Faceted-search vocabulary for the discover page — genres/subjects/languages/
    eras/formats currently in use, so filter chips are driven by real data instead
    of a hardcoded list."""

    genres: list[str] = []
    subjects: list[str] = []
    languages: list[str] = []
    eras: list[str] = []
    original_formats: list[str] = []
    rights_statements: list[str] = []


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