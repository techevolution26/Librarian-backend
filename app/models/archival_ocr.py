from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.archival_canvas import ArchivalCanvas
    from app.models.archival_object import ArchivalObject
    from app.models.book_asset import BookAsset


OCR_STATUSES = {"verified", "stale", "failed"}


class ArchivalOCRPage(Base):
    """Derived OCR text for one archival canvas.

    OCR is presentation/search data derived from an archival asset. It never
    becomes archival metadata and records the source checksum used to produce
    the text so later fixity changes can invalidate it explicitly.
    """

    __tablename__ = "archival_ocr_pages"
    __table_args__ = (
        UniqueConstraint(
            "canvas_id",
            "language",
            "engine",
            "engine_version",
            name="uq_archival_ocr_variant",
        ),
        CheckConstraint("length(trim(text)) > 0", name="ck_archival_ocr_text_nonempty"),
        Index("ix_archival_ocr_pages_object_id", "archival_object_id"),
        Index("ix_archival_ocr_pages_canvas_id", "canvas_id"),
        Index("ix_archival_ocr_pages_asset_id", "source_asset_id"),
        Index("ix_archival_ocr_pages_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    archival_object_id: Mapped[int] = mapped_column(
        ForeignKey("archival_objects.id", ondelete="CASCADE"), nullable=False
    )
    canvas_id: Mapped[int] = mapped_column(
        ForeignKey("archival_canvases.id", ondelete="CASCADE"), nullable=False
    )
    source_asset_id: Mapped[int] = mapped_column(
        ForeignKey("book_assets.id", ondelete="RESTRICT"), nullable=False
    )
    source_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="eng")
    engine: Mapped[str] = mapped_column(String(80), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="verified")
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    archival_object: Mapped["ArchivalObject"] = relationship()
    canvas: Mapped["ArchivalCanvas"] = relationship()
    source_asset: Mapped["BookAsset"] = relationship()
