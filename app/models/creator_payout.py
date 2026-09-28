from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.creator_account import CreatorAccount
    from app.models.creator_revenue_ledger import CreatorRevenueLedgerEntry

CREATOR_PAYOUT_STATUSES = {"requested", "approved", "processing", "paid", "failed", "cancelled"}
CREATOR_PAYOUT_PROVIDER_STATUSES = {"manual", "pending", "processing", "paid", "failed", "cancelled"}


class CreatorPayout(Base):
    """Durable payout instruction and lifecycle record.

    This is a provider-neutral settlement record. It does not itself move money.
    A provider adapter may later attach a provider payout ID/reference and drive
    the lifecycle from processing to paid/failed.
    """

    __tablename__ = "creator_payouts"
    __table_args__ = (
        UniqueConstraint("creator_account_id", "idempotency_key", name="uq_creator_payout_creator_idempotency"),
        Index("ix_creator_payout_creator_account_id", "creator_account_id"),
        Index("ix_creator_payout_status", "status"),
        Index("ix_creator_payout_currency", "currency"),
        CheckConstraint("requested_amount_minor > 0", name="ck_creator_payout_requested_positive"),
        CheckConstraint("eligible_amount_minor > 0", name="ck_creator_payout_eligible_positive"),
        CheckConstraint("requested_amount_minor <= eligible_amount_minor", name="ck_creator_payout_request_within_eligibility"),
        CheckConstraint("char_length(currency) = 3", name="ck_creator_payout_currency_length"),
        CheckConstraint("attempt_count >= 0", name="ck_creator_payout_attempt_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    creator_account_id: Mapped[int] = mapped_column(ForeignKey("creator_accounts.id", ondelete="RESTRICT"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    requested_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    eligible_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="requested")
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider_payout_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    creator_account: Mapped["CreatorAccount"] = relationship()
    allocations: Mapped[list["CreatorPayoutAllocation"]] = relationship(
        back_populates="payout", cascade="all, delete-orphan"
    )


class CreatorPayoutAllocation(Base):
    """Reservation of a creator ledger entry's share for a payout.

    Allocations never alter the immutable revenue ledger. Failed/cancelled
    payouts release their allocations back to eligibility because only active
    payout states are treated as settled/reserved.
    """

    __tablename__ = "creator_payout_allocations"
    __table_args__ = (
        UniqueConstraint("payout_id", "ledger_entry_id", name="uq_creator_payout_allocation_entry"),
        Index("ix_creator_payout_allocation_payout_id", "payout_id"),
        Index("ix_creator_payout_allocation_ledger_entry_id", "ledger_entry_id"),
        CheckConstraint("allocated_amount_minor > 0", name="ck_creator_payout_allocation_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payout_id: Mapped[int] = mapped_column(ForeignKey("creator_payouts.id", ondelete="CASCADE"), nullable=False)
    ledger_entry_id: Mapped[int] = mapped_column(ForeignKey("creator_revenue_ledger_entries.id", ondelete="RESTRICT"), nullable=False)
    allocated_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    payout: Mapped[CreatorPayout] = relationship(back_populates="allocations")
    ledger_entry: Mapped["CreatorRevenueLedgerEntry"] = relationship()
