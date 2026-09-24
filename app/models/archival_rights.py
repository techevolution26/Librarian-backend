from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.archival_object import ArchivalObject


class ArchivalRights(Base):
    """Rights provenance and explicit platform-use policy for an archival object."""

    __tablename__ = "archival_rights"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    archival_object_id: Mapped[int] = mapped_column(
        ForeignKey("archival_objects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    rights_holder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rights_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    copyright_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rights_source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    access_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    reproduction_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    attribution: Mapped[str | None] = mapped_column(Text, nullable=True)
    view_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    download_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    redistribution_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    commercial_use_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
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

    archival_object: Mapped["ArchivalObject"] = relationship(back_populates="rights")
