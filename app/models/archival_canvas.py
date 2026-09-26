from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.archival_object import ArchivalObject
    from app.models.book_asset import BookAsset


class ArchivalCanvas(Base):
    """Logical page/presentation unit belonging to an archival object.

    A canvas is intentionally separate from BookAsset: an asset is a stored
    file/version, while a canvas identifies a logical page or presentation
    unit that may reference an asset without becoming the asset itself.
    """

    __tablename__ = "archival_canvases"
    __table_args__ = (
        UniqueConstraint("archival_object_id", "sequence", name="uq_archival_canvas_sequence"),
        UniqueConstraint("archival_object_id", "canvas_identifier", name="uq_archival_canvas_identifier"),
        CheckConstraint("sequence > 0", name="ck_archival_canvas_sequence_positive"),
        CheckConstraint("page_number IS NULL OR page_number > 0", name="ck_archival_canvas_page_positive"),
        CheckConstraint("width IS NULL OR width > 0", name="ck_archival_canvas_width_positive"),
        CheckConstraint("height IS NULL OR height > 0", name="ck_archival_canvas_height_positive"),
        Index("ix_archival_canvases_object_sequence", "archival_object_id", "sequence"),
        Index("ix_archival_canvases_asset_id", "asset_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    archival_object_id: Mapped[int] = mapped_column(
        ForeignKey("archival_objects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("book_assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    canvas_identifier: Mapped[str] = mapped_column(
        String(120), nullable=False, default=lambda: f"tl:canvas:{uuid4().hex}", index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    archival_object: Mapped["ArchivalObject"] = relationship(back_populates="canvases")
    asset: Mapped["BookAsset | None"] = relationship()
