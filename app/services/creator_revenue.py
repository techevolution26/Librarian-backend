from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.creator_hosted_book import CreatorHostedBook
from app.models.creator_paid_book import CreatorPaidBook
from app.models.creator_revenue_ledger import CreatorRevenueLedgerEntry
from app.schemas.creator_revenue import CreatorRevenueRecordCreate


def record_verified_revenue_event(
    db: Session,
    payload: CreatorRevenueRecordCreate,
) -> CreatorRevenueLedgerEntry:
    existing = db.scalar(
        select(CreatorRevenueLedgerEntry).where(
            CreatorRevenueLedgerEntry.provider == payload.provider,
            CreatorRevenueLedgerEntry.provider_event_id == payload.provider_event_id,
        )
    )
    if existing is not None:
        return existing

    if payload.creator_share_minor + payload.platform_share_minor != payload.gross_amount_minor:
        raise HTTPException(status_code=422, detail="Creator and platform shares must equal gross amount")

    offer = db.get(CreatorPaidBook, payload.paid_offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Paid offer not found")
    if offer.status != "active" and payload.entry_type == "sale":
        raise HTTPException(status_code=409, detail="Only active paid offers can record sales")

    hosted = db.get(CreatorHostedBook, offer.hosted_book_id)
    if hosted is None or hosted.status != "hosted":
        raise HTTPException(status_code=409, detail="The paid offer must belong to an active hosted book")
    if offer.currency.lower() != payload.currency.lower():
        raise HTTPException(status_code=409, detail="Ledger currency must match the paid offer currency")

    entry = CreatorRevenueLedgerEntry(
        creator_account_id=offer.creator_account_id,
        hosted_book_id=offer.hosted_book_id,
        paid_offer_id=offer.id,
        buyer_user_id=payload.buyer_user_id,
        entry_type=payload.entry_type,
        gross_amount_minor=payload.gross_amount_minor,
        creator_share_minor=payload.creator_share_minor,
        platform_share_minor=payload.platform_share_minor,
        currency=payload.currency.lower(),
        provider=payload.provider,
        provider_event_id=payload.provider_event_id,
        provider_reference=payload.provider_reference.strip() if payload.provider_reference else None,
        occurred_at=payload.occurred_at,
    )
    db.add(entry)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(
            select(CreatorRevenueLedgerEntry).where(
                CreatorRevenueLedgerEntry.provider == payload.provider,
                CreatorRevenueLedgerEntry.provider_event_id == payload.provider_event_id,
            )
        )
        if existing is not None:
            return existing
        raise HTTPException(status_code=409, detail="Revenue event could not be recorded") from exc
    db.refresh(entry)
    return entry


def build_creator_revenue_summary(db: Session, creator_account_id: int):
    entries = db.scalars(
        select(CreatorRevenueLedgerEntry)
        .where(CreatorRevenueLedgerEntry.creator_account_id == creator_account_id)
        .order_by(CreatorRevenueLedgerEntry.occurred_at.desc(), CreatorRevenueLedgerEntry.id.desc())
    ).all()

    # Entries are immutable. Reversals/adjustments are compensating records;
    # their values are subtracted from the gross/creator/platform totals.
    sign = lambda entry: -1 if entry.entry_type in {"reversal", "adjustment"} else 1
    gross = sum(sign(e) * e.gross_amount_minor for e in entries)
    creator = sum(sign(e) * e.creator_share_minor for e in entries)
    platform = sum(sign(e) * e.platform_share_minor for e in entries)
    currencies = sorted({e.currency for e in entries})
    from app.schemas.creator_revenue import CreatorRevenueSummary
    return CreatorRevenueSummary(
        entry_count=len(entries),
        gross_amount_minor=max(gross, 0),
        creator_share_minor=max(creator, 0),
        platform_share_minor=max(platform, 0),
        currencies=currencies,
        entries=entries,
    )
