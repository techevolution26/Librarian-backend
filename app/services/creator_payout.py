from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.creator_account import CreatorAccount
from app.models.creator_payout import CreatorPayout, CreatorPayoutAllocation
from app.models.creator_revenue_ledger import CreatorRevenueLedgerEntry

ACTIVE_PAYOUT_STATUSES = {"requested", "approved", "processing", "paid"}


def _signed_share(entry: CreatorRevenueLedgerEntry) -> int:
    return -entry.creator_share_minor if entry.entry_type in {"reversal", "adjustment"} else entry.creator_share_minor


def get_creator_payout_balances(db: Session, creator_account_id: int) -> list[dict[str, int | str]]:
    entries = db.scalars(
        select(CreatorRevenueLedgerEntry)
        .where(CreatorRevenueLedgerEntry.creator_account_id == creator_account_id)
    ).all()
    allocated_rows = db.execute(
        select(CreatorPayout.currency, func.coalesce(func.sum(CreatorPayoutAllocation.allocated_amount_minor), 0))
        .join(CreatorPayoutAllocation, CreatorPayoutAllocation.payout_id == CreatorPayout.id)
        .where(
            CreatorPayout.creator_account_id == creator_account_id,
            CreatorPayout.status.in_(ACTIVE_PAYOUT_STATUSES),
        )
        .group_by(CreatorPayout.currency)
    ).all()
    allocated_by_currency = {currency: int(amount) for currency, amount in allocated_rows}

    ledger_by_currency: dict[str, int] = {}
    for entry in entries:
        ledger_by_currency[entry.currency] = ledger_by_currency.get(entry.currency, 0) + _signed_share(entry)

    currencies = sorted(set(ledger_by_currency) | set(allocated_by_currency))
    return [
        {
            "currency": currency,
            "ledger_creator_share_minor": ledger_by_currency.get(currency, 0),
            "allocated_active_minor": allocated_by_currency.get(currency, 0),
            "eligible_balance_minor": ledger_by_currency.get(currency, 0) - allocated_by_currency.get(currency, 0),
        }
        for currency in currencies
    ]


def request_creator_payout(
    db: Session,
    *,
    creator_account_id: int,
    currency: str,
    amount_minor: int,
    idempotency_key: str,
) -> CreatorPayout:
    existing = db.scalar(
        select(CreatorPayout).where(
            CreatorPayout.creator_account_id == creator_account_id,
            CreatorPayout.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.currency != currency or existing.requested_amount_minor != amount_minor:
            raise HTTPException(status_code=409, detail="Idempotency key was already used for a different payout request")
        return existing

    # Serialise payout creation per creator where the database supports row locks.
    account = db.scalar(
        select(CreatorAccount).where(CreatorAccount.id == creator_account_id).with_for_update()
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Creator account not found")

    balances = get_creator_payout_balances(db, creator_account_id)
    balance = next((row for row in balances if row["currency"] == currency), None)
    eligible = int(balance["eligible_balance_minor"]) if balance else 0
    if eligible <= 0:
        raise HTTPException(status_code=409, detail="No eligible payout balance is available for this currency")
    if amount_minor > eligible:
        raise HTTPException(status_code=409, detail="Requested payout exceeds the eligible creator balance")

    now = datetime.now(timezone.utc)
    payout = CreatorPayout(
        creator_account_id=creator_account_id,
        currency=currency,
        requested_amount_minor=amount_minor,
        eligible_amount_minor=eligible,
        status="requested",
        provider_idempotency_key=f"librarian-payout-{uuid4().hex}",
        idempotency_key=idempotency_key,
        requested_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(payout)
    db.flush()

    # Reserve only positive ledger shares. Reversals/adjustments remain negative
    # carry-forward in the balance calculation and are never silently paid out.
    positive_entries = db.scalars(
        select(CreatorRevenueLedgerEntry)
        .where(
            CreatorRevenueLedgerEntry.creator_account_id == creator_account_id,
            CreatorRevenueLedgerEntry.currency == currency,
            CreatorRevenueLedgerEntry.entry_type.in_(["sale", "adjustment"]),
            CreatorRevenueLedgerEntry.creator_share_minor > 0,
        )
        .order_by(CreatorRevenueLedgerEntry.occurred_at.asc(), CreatorRevenueLedgerEntry.id.asc())
        .with_for_update()
    ).all()

    allocated_rows = db.execute(
        select(
            CreatorPayoutAllocation.ledger_entry_id,
            func.coalesce(func.sum(CreatorPayoutAllocation.allocated_amount_minor), 0),
        )
        .join(CreatorPayout, CreatorPayout.id == CreatorPayoutAllocation.payout_id)
        .where(
            CreatorPayout.creator_account_id == creator_account_id,
            CreatorPayout.status.in_(ACTIVE_PAYOUT_STATUSES),
        )
        .group_by(CreatorPayoutAllocation.ledger_entry_id)
    ).all()
    allocated_by_entry = {entry_id: int(amount) for entry_id, amount in allocated_rows}

    remaining = amount_minor
    for entry in positive_entries:
        available = entry.creator_share_minor - allocated_by_entry.get(entry.id, 0)
        if available <= 0:
            continue
        allocation_amount = min(available, remaining)
        db.add(
            CreatorPayoutAllocation(
                payout_id=payout.id,
                ledger_entry_id=entry.id,
                allocated_amount_minor=allocation_amount,
            )
        )
        remaining -= allocation_amount
        if remaining == 0:
            break

    if remaining != 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="Eligible payout balance changed; please retry the request")

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(
            select(CreatorPayout).where(
                CreatorPayout.creator_account_id == creator_account_id,
                CreatorPayout.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return existing
        raise HTTPException(status_code=409, detail="Payout request could not be created") from exc
    db.refresh(payout)
    return payout


def list_creator_payouts(db: Session, creator_account_id: int) -> list[CreatorPayout]:
    return db.scalars(
        select(CreatorPayout)
        .where(CreatorPayout.creator_account_id == creator_account_id)
        .order_by(CreatorPayout.created_at.desc(), CreatorPayout.id.desc())
    ).all()


def _get_payout_for_update(db: Session, payout_id: int) -> CreatorPayout:
    payout = db.scalar(select(CreatorPayout).where(CreatorPayout.id == payout_id).with_for_update())
    if payout is None:
        raise HTTPException(status_code=404, detail="Payout not found")
    return payout


def approve_creator_payout(db: Session, payout_id: int) -> CreatorPayout:
    payout = _get_payout_for_update(db, payout_id)
    if payout.status != "requested":
        raise HTTPException(status_code=409, detail="Only requested payouts can be approved")
    payout.status = "approved"
    payout.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(payout)
    return payout


def begin_creator_payout(db: Session, payout_id: int, provider: str) -> CreatorPayout:
    payout = _get_payout_for_update(db, payout_id)
    if payout.status not in {"approved", "failed"}:
        raise HTTPException(status_code=409, detail="Only approved or failed payouts can enter processing")
    if payout.status == "failed":
        balances = get_creator_payout_balances(db, payout.creator_account_id)
        balance = next((row for row in balances if row["currency"] == payout.currency), None)
        eligible = int(balance["eligible_balance_minor"]) if balance else 0
        if eligible < payout.requested_amount_minor:
            raise HTTPException(status_code=409, detail="Payout cannot be retried because the current eligible balance is insufficient")
    payout.status = "processing"
    payout.provider = provider.strip()
    payout.attempt_count = (payout.attempt_count or 0) + 1
    payout.processing_at = datetime.now(timezone.utc)
    payout.failure_code = None
    payout.failure_message = None
    db.commit()
    db.refresh(payout)
    return payout


def complete_creator_payout(
    db: Session,
    payout_id: int,
    *,
    provider_payout_id: str | None,
    provider_reference: str | None,
) -> CreatorPayout:
    payout = _get_payout_for_update(db, payout_id)
    if payout.status != "processing":
        raise HTTPException(status_code=409, detail="Only processing payouts can be completed")
    payout.status = "paid"
    payout.provider_payout_id = provider_payout_id.strip() if provider_payout_id else None
    payout.provider_reference = provider_reference.strip() if provider_reference else None
    payout.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(payout)
    return payout


def fail_creator_payout(db: Session, payout_id: int, failure_code: str, failure_message: str) -> CreatorPayout:
    payout = _get_payout_for_update(db, payout_id)
    if payout.status != "processing":
        raise HTTPException(status_code=409, detail="Only processing payouts can fail")
    payout.status = "failed"
    payout.failure_code = failure_code.strip()
    payout.failure_message = failure_message.strip()
    payout.failed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(payout)
    return payout


def cancel_creator_payout(db: Session, payout_id: int) -> CreatorPayout:
    payout = _get_payout_for_update(db, payout_id)
    if payout.status not in {"requested", "approved"}:
        raise HTTPException(status_code=409, detail="Only requested or approved payouts can be cancelled")
    payout.status = "cancelled"
    payout.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(payout)
    return payout
