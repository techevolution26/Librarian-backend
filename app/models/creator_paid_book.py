from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.creator_account import CreatorAccount
    from app.models.creator_hosted_book import CreatorHostedBook


CREATOR_PAID_BOOK_STATUSES = {"draft", "active", "archived"}


class CreatorPaidBook(Base):
    """Commercial offer definition for a creator-hosted book.

    This is pricing/catalog configuration only. It does not represent a
    purchase, entitlement, payout, or Stripe transaction. Those concerns are
    intentionally introduced by later Creator Economy / Subscription tackles.
    """

    __tablename__ = "creator_paid_books"
    __table_args__ = (
        UniqueConstraint("hosted_book_id", name="uq_creator_paid_books_hosted_book_id"),
        Index("ix_creator_paid_books_creator_account_id", "creator_account_id"),
        Index("ix_creator_paid_books_status", "status"),
        CheckConstraint("price_amount_minor > 0", name="ck_creator_paid_books_price_positive"),
        CheckConstraint("char_length(currency) = 3", name="ck_creator_paid_books_currency_length"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hosted_book_id: Mapped[int] = mapped_column(
        ForeignKey("creator_hosted_books.id", ondelete="CASCADE"), nullable=False
    )
    creator_account_id: Mapped[int] = mapped_column(
        ForeignKey("creator_accounts.id", ondelete="CASCADE"), nullable=False
    )
    price_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    hosted_book: Mapped["CreatorHostedBook"] = relationship()
    creator_account: Mapped["CreatorAccount"] = relationship()
