from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.creator_hosted_book import CreatorHostedBook
    from app.models.creator_paid_book import CreatorPaidBook
    from app.models.purchase import Purchase
    from app.models.user import User


CREATOR_LIFETIME_ACCESS_STATUSES = {"active", "revoked"}
CREATOR_LIFETIME_ACCESS_SOURCES = {"purchase", "manual", "admin"}


class CreatorLifetimeAccess(Base):
    """Durable lifetime ownership of a creator-hosted book.

    Ownership is intentionally independent of payment. A later payment
    fulfillment workflow can create/activate this record after a verified
    purchase without treating a checkout session as ownership itself.
    """

    __tablename__ = "creator_lifetime_access"
    __table_args__ = (
        UniqueConstraint("user_id", "hosted_book_id", name="uq_creator_lifetime_access_user_hosted_book"),
        UniqueConstraint("purchase_id", name="uq_creator_lifetime_access_purchase_id"),
        Index("ix_creator_lifetime_access_user_id", "user_id"),
        Index("ix_creator_lifetime_access_hosted_book_id", "hosted_book_id"),
        Index("ix_creator_lifetime_access_status", "status"),
        Index("ix_creator_lifetime_access_purchase_id", "purchase_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    hosted_book_id: Mapped[int] = mapped_column(
        ForeignKey("creator_hosted_books.id", ondelete="RESTRICT"), nullable=False
    )
    purchase_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchases.id", ondelete="SET NULL"), nullable=True
    )
    paid_offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("creator_paid_books.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    access_source: Mapped[str] = mapped_column(String(20), nullable=False, default="purchase")
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    user: Mapped["User"] = relationship()
    hosted_book: Mapped["CreatorHostedBook"] = relationship()
    paid_offer: Mapped["CreatorPaidBook | None"] = relationship()
    purchase: Mapped["Purchase | None"] = relationship()
