from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.creator_account import CreatorAccount
    from app.models.creator_book_submission import CreatorBookSubmission


CREATOR_HOSTED_BOOK_STATUSES = {"draft", "hosted", "archived"}


class CreatorHostedBook(Base):
    """Private creator-hosting bridge between a submission and a catalog Book.

    A hosted book owns a draft Book identity and its private BookAsset. It is
    deliberately not a publication record: visibility remains draft until a
    later, explicit publishing workflow authorizes public catalog access.
    """

    __tablename__ = "creator_hosted_books"
    __table_args__ = (
        UniqueConstraint("submission_id", name="uq_creator_hosted_books_submission_id"),
        UniqueConstraint("book_id", name="uq_creator_hosted_books_book_id"),
        Index("ix_creator_hosted_books_creator_account_id", "creator_account_id"),
        Index("ix_creator_hosted_books_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("creator_book_submissions.id", ondelete="CASCADE"), nullable=False
    )
    creator_account_id: Mapped[int] = mapped_column(
        ForeignKey("creator_accounts.id", ondelete="CASCADE"), nullable=False
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    submission: Mapped["CreatorBookSubmission"] = relationship()
    creator_account: Mapped["CreatorAccount"] = relationship()
    book: Mapped["Book"] = relationship()
