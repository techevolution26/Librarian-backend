from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.book import Book
    from app.models.archival_object import ArchivalObject
    from app.models.book_asset import BookAsset
    from app.models.archival_canvas import ArchivalCanvas
    from app.models.archival_ocr import ArchivalOCRPage


READER_SOURCE_LOCATOR_TYPES = {
    "pdf_page",
    "pdf_text",
    "iiif_canvas",
    "image_region",
    "text_span",
    "ocr_span",
    "media_time",
}


class ReaderSourceAnchor(Base):
    """Immutable, user-owned pointer to a precise location in a source version.

    This is private Reader research context. It never grants archival authority
    and never mutates Book, ArchivalObject, BookAsset, Canvas, OCR or Circle data.
    """

    __tablename__ = "reader_source_anchors"
    __table_args__ = (
        CheckConstraint(
            "locator_type IN ('pdf_page', 'pdf_text', 'iiif_canvas', 'image_region', 'text_span', 'ocr_span', 'media_time')",
            name="ck_reader_source_anchor_locator_type",
        ),
        Index("ix_reader_source_anchors_user_book", "user_id", "book_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    archival_object_id: Mapped[int | None] = mapped_column(
        ForeignKey("archival_objects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("book_assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    canvas_id: Mapped[int | None] = mapped_column(
        ForeignKey("archival_canvases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ocr_page_id: Mapped[int | None] = mapped_column(
        ForeignKey("archival_ocr_pages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    locator_type: Mapped[str] = mapped_column(String(30), nullable=False)
    locator_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Immutable snapshots keep a useful citation even if a source relationship
    # is later retired or a physical asset is replaced.
    source_persistent_identifier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_accession_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_canvas_identifier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_asset_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_asset_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_text_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")
    book: Mapped["Book"] = relationship("Book")
    archival_object: Mapped["ArchivalObject | None"] = relationship("ArchivalObject")
    source_asset: Mapped["BookAsset | None"] = relationship("BookAsset")
    canvas: Mapped["ArchivalCanvas | None"] = relationship("ArchivalCanvas")
    ocr_page: Mapped["ArchivalOCRPage | None"] = relationship("ArchivalOCRPage")
