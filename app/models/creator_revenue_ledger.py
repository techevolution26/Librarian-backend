from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.creator_account import CreatorAccount
    from app.models.creator_hosted_book import CreatorHostedBook
    from app.models.creator_paid_book import CreatorPaidBook
    from app.models.user import User


CREATOR_REVENUE_ENTRY_TYPES = {"sale", "reversal", "adjustment"}


class CreatorRevenueLedgerEntry(Base):
    """Immutable accounting entry created only from a verified commercial event.

    Corrections are represented by new compensating entries; existing entries
    are never edited or deleted. This model is not a payment transaction and
    does not execute payouts.
    """

    __tablename__ = "creator_revenue_ledger_entries"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_creator_revenue_provider_event"),
        Index("ix_creator_revenue_creator_account_id", "creator_account_id"),
        Index("ix_creator_revenue_hosted_book_id", "hosted_book_id"),
        Index("ix_creator_revenue_paid_offer_id", "paid_offer_id"),
        Index("ix_creator_revenue_buyer_user_id", "buyer_user_id"),
        Index("ix_creator_revenue_occurred_at", "occurred_at"),
        CheckConstraint("gross_amount_minor > 0", name="ck_creator_revenue_gross_positive"),
        CheckConstraint("creator_share_minor >= 0", name="ck_creator_revenue_creator_share_nonnegative"),
        CheckConstraint("platform_share_minor >= 0", name="ck_creator_revenue_platform_share_nonnegative"),
        CheckConstraint("creator_share_minor + platform_share_minor = gross_amount_minor", name="ck_creator_revenue_shares_balance"),
        CheckConstraint("char_length(currency) = 3", name="ck_creator_revenue_currency_length"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    creator_account_id: Mapped[int] = mapped_column(ForeignKey("creator_accounts.id", ondelete="RESTRICT"), nullable=False)
    hosted_book_id: Mapped[int] = mapped_column(ForeignKey("creator_hosted_books.id", ondelete="RESTRICT"), nullable=False)
    paid_offer_id: Mapped[int] = mapped_column(ForeignKey("creator_paid_books.id", ondelete="RESTRICT"), nullable=False)
    buyer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False, default="sale")
    gross_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    creator_share_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_share_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    creator_account: Mapped["CreatorAccount"] = relationship()
    hosted_book: Mapped["CreatorHostedBook"] = relationship()
    paid_offer: Mapped["CreatorPaidBook"] = relationship()
    buyer_user: Mapped["User | None"] = relationship()
