from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.creator_hosted_book import CreatorHostedBook
    from app.models.creator_paid_book import CreatorPaidBook
    from app.models.user import User


PURCHASE_STATUSES = {"pending", "paid", "failed", "cancelled", "refunded"}
PURCHASE_PROVIDERS = {"stripe"}


class Purchase(Base):
    """A verified-capable record of a one-time book purchase.

    Purchase state is payment/transaction state. It is intentionally separate
    from the entitlement that grants access and from creator revenue/payout
    accounting.
    """

    __tablename__ = "purchases"
    __table_args__ = (
        UniqueConstraint("provider", "provider_checkout_session_id", name="uq_purchase_provider_checkout_session"),
        UniqueConstraint("provider", "provider_payment_intent_id", name="uq_purchase_provider_payment_intent"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_purchase_user_idempotency"),
        Index("ix_purchases_user_id", "user_id"),
        Index("ix_purchases_paid_offer_id", "paid_offer_id"),
        Index("ix_purchases_status", "status"),
        CheckConstraint("amount_minor > 0", name="ck_purchase_amount_positive"),
        CheckConstraint("char_length(currency) = 3", name="ck_purchase_currency_length"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    paid_offer_id: Mapped[int] = mapped_column(ForeignKey("creator_paid_books.id", ondelete="RESTRICT"), nullable=False)
    hosted_book_id: Mapped[int] = mapped_column(ForeignKey("creator_hosted_books.id", ondelete="RESTRICT"), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="stripe")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    user: Mapped["User"] = relationship()
    paid_offer: Mapped["CreatorPaidBook"] = relationship()
    hosted_book: Mapped["CreatorHostedBook"] = relationship()
