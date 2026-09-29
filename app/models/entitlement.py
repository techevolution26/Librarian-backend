from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


ENTITLEMENT_TYPES = {"book_access", "feature_access"}
ENTITLEMENT_SOURCES = {"lifetime_access", "purchase", "subscription", "admin", "system"}
ENTITLEMENT_STATUSES = {"active", "revoked"}


class Entitlement(Base):
    """Authoritative grant of a user capability or book access.

    Payment, revenue accounting, and payout records are deliberately not
    represented here. An entitlement only answers whether a user has been
    granted access and for how long.
    """

    __tablename__ = "entitlements"
    __table_args__ = (
        UniqueConstraint("user_id", "entitlement_type", "book_id", "feature_key", "source", "source_reference", name="uq_entitlement_source"),
        Index("ix_entitlements_user_id", "user_id"),
        Index("ix_entitlements_book_id", "book_id"),
        Index("ix_entitlements_feature_key", "feature_key"),
        Index("ix_entitlements_status", "status"),
        CheckConstraint(
            "(entitlement_type = 'book_access' AND book_id IS NOT NULL AND feature_key IS NULL) "
            "OR (entitlement_type = 'feature_access' AND book_id IS NULL AND feature_key IS NOT NULL)",
            name="ck_entitlement_scope_matches_type",
        ),
        CheckConstraint("expires_at IS NULL OR expires_at > starts_at", name="ck_entitlement_expiry_after_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entitlement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=True)
    feature_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    user: Mapped["User"] = relationship()
