from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.archival_object import ArchivalObject


class ArchivalMetadata(Base):
    """Structured intellectual metadata attached to an archival object."""

    __tablename__ = "archival_metadata"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    archival_object_id: Mapped[int] = mapped_column(
        ForeignKey("archival_objects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    alternative_titles: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    contributors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    language: Mapped[str | None] = mapped_column(String(40), nullable=True)
    subjects: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    genre: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    edition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
        back_populates="intellectual_metadata"
    )
