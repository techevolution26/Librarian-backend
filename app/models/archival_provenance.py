from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.archival_object import ArchivalObject


class ArchivalProvenance(Base):
    """Physical and digital provenance for an archival object."""

    __tablename__ = "archival_provenance"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    archival_object_id: Mapped[int] = mapped_column(
        ForeignKey("archival_objects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    source_institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_collection: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shelfmark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accession_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    original_format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    physical_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin_place: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origin_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    digitized_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    digitized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    digitization_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scanner_device: Mapped[str | None] = mapped_column(String(255), nullable=True)
    master_format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    derivative_format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    software: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    archival_object: Mapped["ArchivalObject"] = relationship(
        back_populates="provenance"
    )
