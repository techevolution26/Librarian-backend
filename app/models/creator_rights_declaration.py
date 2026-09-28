from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.creator_account import CreatorAccount
    from app.models.creator_book_submission import CreatorBookSubmission
    from app.models.user import User


CREATOR_RIGHTS_BASIS = {
    "original_author",
    "copyright_holder",
    "authorized_representative",
    "licensed",
    "public_domain",
    "other",
}

CREATOR_RIGHTS_DECLARATION_STATUSES = {"active", "superseded"}


class CreatorRightsDeclaration(Base):
    """Immutable, versioned rights assertion attached to a creator submission."""

    __tablename__ = "creator_rights_declarations"
    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            "version",
            name="uq_creator_rights_declaration_submission_version",
        ),
        Index("ix_creator_rights_declarations_submission_id", "submission_id"),
        Index("ix_creator_rights_declarations_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("creator_book_submissions.id", ondelete="CASCADE"), nullable=False
    )
    creator_account_id: Mapped[int] = mapped_column(
        ForeignKey("creator_accounts.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    rights_basis: Mapped[str] = mapped_column(String(40), nullable=False)
    rights_holder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rights_statement: Mapped[str] = mapped_column(Text, nullable=False)
    territory: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hosting_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    public_display_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    download_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    redistribution_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    commercial_use_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    derivative_use_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    declaration_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    attestation_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    declared_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    declared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    submission: Mapped["CreatorBookSubmission"] = relationship(
        back_populates="rights_declarations"
    )
    creator_account: Mapped["CreatorAccount"] = relationship()
    declared_by: Mapped["User"] = relationship(foreign_keys=[declared_by_user_id])
