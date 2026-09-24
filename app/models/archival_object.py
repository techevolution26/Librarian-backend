from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.collection import Collection
    from app.models.archival_metadata import ArchivalMetadata
    from app.models.archival_provenance import ArchivalProvenance
    from app.models.archival_rights import ArchivalRights


ARCHIVAL_OBJECT_TYPES = {
    "book",
    "manuscript",
    "newspaper",
    "photograph",
    "map",
    "audio",
    "video",
    "document",
    "oral_history",
    "other",
}

ARCHIVAL_OBJECT_VISIBILITIES = {"draft", "published", "restricted"}


class ArchivalObject(Base):
    """Stable archival identity shared by present and future object formats."""

    __tablename__ = "archival_objects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    identifier: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    object_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    collection_id: Mapped[int | None] = mapped_column(
        ForeignKey("collections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(
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

    collection: Mapped["Collection | None"] = relationship(
        back_populates="archival_objects"
    )
    book: Mapped["Book | None"] = relationship(
        back_populates="archival_object", uselist=False
    )
    intellectual_metadata: Mapped["ArchivalMetadata | None"] = relationship(
        back_populates="archival_object", uselist=False, cascade="all, delete-orphan"
    )
    provenance: Mapped["ArchivalProvenance | None"] = relationship(
        back_populates="archival_object", uselist=False, cascade="all, delete-orphan"
    )
    rights: Mapped["ArchivalRights | None"] = relationship(
        back_populates="archival_object", uselist=False, cascade="all, delete-orphan"
    )
