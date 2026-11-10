from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


RESOURCE_CONTRIBUTION_STATUSES = {
    "submitted",
    "under_review",
    "changes_requested",
    "rejected",
    "approved",
    "withdrawn",
}
RESOURCE_CONTRIBUTION_MATERIAL_TYPES = {"pdf", "text", "facsimile"}
RESOURCE_CONTRIBUTION_RIGHTS_BASES = {
    "created_by_contributor",
    "permission_granted",
    "public_domain",
    "open_license",
    "unknown",
}


class ResourceContribution(Base):
    """Private community-submitted material awaiting curator acceptance."""

    __tablename__ = "resource_contributions"
    __table_args__ = (
        Index("ix_resource_contributions_status_submitted", "status", "submitted_at"),
        Index("ix_resource_contributions_contributor_status", "contributor_user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    contributor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    material_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="submitted", index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(40), nullable=False, default="en")
    genre_csv: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    subjects_csv: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    original_format: Mapped[str] = mapped_column(String(30), nullable=False, default="born-digital")
    archival_object_type: Mapped[str] = mapped_column(String(30), nullable=False, default="document")
    origin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    era: Mapped[str | None] = mapped_column(String(120), nullable=True)
    condition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_collection: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shelfmark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provenance_accession_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    digitized_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    digitization_method: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scanner_device: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preservation_master_format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    derivative_format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    software: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Contributor declarations are evidence for curator review, never an access decision.
    rights_statement: Mapped[str] = mapped_column(String(30), nullable=False, default="all-rights-reserved")
    rights_holder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rights_basis: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    rights_evidence: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    accuracy_attested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    contributor_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    imported_book_id: Mapped[int | None] = mapped_column(
        ForeignKey("books.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    contributor: Mapped["User"] = relationship(foreign_keys=[contributor_user_id])
    reviewed_by: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by_user_id])
    imported_book: Mapped["Book | None"] = relationship()
    assets: Mapped[list["ResourceContributionAsset"]] = relationship(
        back_populates="contribution", cascade="all, delete-orphan", order_by="ResourceContributionAsset.sequence.asc()"
    )

    @property
    def genres(self) -> list[str]:
        return [value.strip() for value in self.genre_csv.split(",") if value.strip()]

    @property
    def subjects(self) -> list[str]:
        return [value.strip() for value in self.subjects_csv.split(",") if value.strip()]


class ResourceContributionAsset(Base):
    """Private staged attachment; storage keys are never returned by submission APIs."""

    __tablename__ = "resource_contribution_assets"
    __table_args__ = (
        Index("ix_resource_contribution_assets_contribution_sequence", "contribution_id", "sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    contribution_id: Mapped[int] = mapped_column(
        ForeignKey("resource_contributions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_role: Mapped[str] = mapped_column(String(20), nullable=False)  # primary | canvas
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imported_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("book_assets.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    contribution: Mapped[ResourceContribution] = relationship(back_populates="assets")
    imported_asset = relationship("BookAsset")
