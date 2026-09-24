from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.archival_object import ArchivalObject
    from app.models.book_asset import BookAsset


PRESERVATION_EVENT_TYPES = {
    "ingestion",
    "validation",
    "checksum_generated",
    "checksum_verified",
    "derivative_created",
    "migration",
    "storage_replication",
    "restore",
    "fixity_check",
    "access_copy_created",
}

PRESERVATION_EVENT_OUTCOMES = {
    "success",
    "failure",
    "warning",
    "unknown",
}


class PreservationEvent(Base):
    """Append-only preservation history for an archival object or asset."""

    __tablename__ = "preservation_events"
    __table_args__ = (
        Index("ix_preservation_events_object_date", "archival_object_id", "event_date"),
        Index("ix_preservation_events_asset_date", "asset_id", "event_date"),
        Index("ix_preservation_events_type_date", "event_type", "event_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    archival_object_id: Mapped[int] = mapped_column(
        ForeignKey("archival_objects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("book_assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    target_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checksum_algorithm: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    archival_object: Mapped["ArchivalObject"] = relationship(back_populates="preservation_events")
    asset: Mapped["BookAsset | None"] = relationship()
