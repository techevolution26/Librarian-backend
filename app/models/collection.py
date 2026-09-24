from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


COLLECTION_VISIBILITIES = {"draft", "published", "restricted"}


if TYPE_CHECKING:
    from app.models.archival_object import ArchivalObject


class Collection(Base):
    """A curated archival grouping; archival objects will attach to it in the next domain step."""

    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    identifier: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    curator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    geographic_scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_start: Mapped[str | None] = mapped_column(String(40), nullable=True)
    date_end: Mapped[str | None] = mapped_column(String(40), nullable=True)
    subjects_csv: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    rights_statement: Mapped[str | None] = mapped_column(String(500), nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archival_objects: Mapped[list["ArchivalObject"]] = relationship(
        "ArchivalObject", back_populates="collection"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def subjects(self) -> list[str]:
        return [value.strip() for value in self.subjects_csv.split(",") if value.strip()]

    @subjects.setter
    def subjects(self, values: list[str]) -> None:
        self.subjects_csv = ",".join(value.strip() for value in values if value.strip())
