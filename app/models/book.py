from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.library_item import LibraryItem
    from app.models.book_asset import BookAsset


# Archival vocabulary — kept as free-text/CSV columns (not lookup tables) to match
# the existing genre_csv pattern in this codebase. Values are conventions, not
# hard constraints, so admins are never blocked by an unrecognised term.
ORIGINAL_FORMATS = {"born-digital", "printed", "manuscript", "oral-transcription"}
RIGHTS_STATEMENTS = {"public-domain", "cc-by", "all-rights-reserved", "restricted"}


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cover: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=0)
    pages: Mapped[int] = mapped_column(Integer, default=0)
    genre_csv: Mapped[str] = mapped_column(String(255), default="")
    source_type: Mapped[str] = mapped_column(String(30), default="text")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="published")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cover_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # --- Archival / provenance metadata (the "Librarian archive shape") ---
    accession_no: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(40), default="en")
    subjects_csv: Mapped[str] = mapped_column(String(255), default="")
    origin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    era: Mapped[str | None] = mapped_column(String(120), nullable=True)
    original_format: Mapped[str] = mapped_column(String(30), default="born-digital")
    rights_statement: Mapped[str] = mapped_column(String(30), default="all-rights-reserved")
    condition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    curator_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    digitized_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    digitized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assets: Mapped[list["BookAsset"]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="BookAsset.created_at.desc()",
    )

    library_items: Mapped[list["LibraryItem"]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
    )

    @property
    def genres(self) -> list[str]:
        return [g for g in self.genre_csv.split(",") if g]

    @genres.setter
    def genres(self, values: list[str]) -> None:
        self.genre_csv = ",".join(v.strip() for v in values if v.strip())

    @property
    def tags(self) -> list[str]:
        return self.genres

    @tags.setter
    def tags(self, values: list[str]) -> None:
        self.genres = values

    @property
    def genre(self) -> list[str]:
        return self.genres

    @genre.setter
    def genre(self, values: list[str]) -> None:
        self.genres = values

    @property
    def subjects(self) -> list[str]:
        return [s for s in self.subjects_csv.split(",") if s]

    @subjects.setter
    def subjects(self, values: list[str]) -> None:
        self.subjects_csv = ",".join(v.strip() for v in values if v.strip())

    @property
    def is_archival_format(self) -> bool:
        """True for anything that started life off-screen (manuscript, print, oral)."""
        return self.original_format != "born-digital"

    @property
    def authors(self) -> list[str]:
        return [a.strip() for a in self.author.split(",") if a.strip()]

    @authors.setter
    def authors(self, values: list[str]) -> None:
        self.author = ", ".join(v.strip() for v in values if v.strip())

    @property
    def content_type(self) -> str:
        return self.source_type

    @content_type.setter
    def content_type(self, value: str) -> None:
        self.source_type = value