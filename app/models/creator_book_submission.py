from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.creator_account import CreatorAccount
    from app.models.creator_rights_declaration import CreatorRightsDeclaration
    from app.models.user import User


CREATOR_SUBMISSION_STATUSES = {
    "draft",
    "submitted",
    "under_review",
    "changes_requested",
}


class CreatorBookSubmission(Base):
    __tablename__ = "creator_book_submissions"
    __table_args__ = (
        Index("ix_creator_book_submissions_creator_account_id", "creator_account_id"),
        Index("ix_creator_book_submissions_status", "status"),
        Index("ix_creator_book_submissions_submitted_at", "submitted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    creator_account_id: Mapped[int] = mapped_column(
        ForeignKey("creator_accounts.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(40), nullable=False, default="en")
    genre_csv: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    creator_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    creator_account: Mapped["CreatorAccount"] = relationship(back_populates="book_submissions")
    reviewed_by: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by_user_id])
    rights_declarations: Mapped[list["CreatorRightsDeclaration"]] = relationship(
        back_populates="submission", order_by="CreatorRightsDeclaration.version.desc()"
    )

    @property
    def genres(self) -> list[str]:
        return [value.strip() for value in self.genre_csv.split(",") if value.strip()]

    @genres.setter
    def genres(self, values: list[str]) -> None:
        self.genre_csv = ",".join(value.strip() for value in values if value.strip())
