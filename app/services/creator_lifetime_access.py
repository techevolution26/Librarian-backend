from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.creator_hosted_book import CreatorHostedBook
from app.models.creator_lifetime_access import CreatorLifetimeAccess
from app.models.purchase import Purchase
from app.services.entitlements import grant_book_entitlement, revoke_book_entitlement


def _now() -> datetime:
    return datetime.now(timezone.utc)


def grant_lifetime_access_from_purchase(db: Session, purchase: Purchase) -> CreatorLifetimeAccess:
    """Materialize durable ownership from a verified paid purchase.

    The purchase remains the transaction record. This ownership row becomes
    the durable relationship, and its entitlement is the access authority.
    """
    hosted = db.get(CreatorHostedBook, purchase.hosted_book_id)
    if hosted is None:
        raise ValueError("Purchase references a missing hosted book")

    existing = db.scalar(
        select(CreatorLifetimeAccess).where(
            CreatorLifetimeAccess.user_id == purchase.user_id,
            CreatorLifetimeAccess.hosted_book_id == purchase.hosted_book_id,
        )
    )
    now = purchase.purchased_at or _now()

    if existing is None:
        existing = CreatorLifetimeAccess(
            user_id=purchase.user_id,
            hosted_book_id=purchase.hosted_book_id,
            purchase_id=purchase.id,
            paid_offer_id=purchase.paid_offer_id,
            status="active",
            access_source="purchase",
            granted_at=now,
        )
        db.add(existing)
        db.flush()
    else:
        existing.status = "active"
        existing.revoked_at = None
        existing.purchase_id = purchase.id
        existing.paid_offer_id = purchase.paid_offer_id
        existing.access_source = "purchase"
        existing.granted_at = existing.granted_at or now
        db.flush()

    grant_book_entitlement(
        db,
        user_id=purchase.user_id,
        book_id=hosted.book_id,
        source="lifetime_access",
        source_reference=f"creator_lifetime_access:{existing.id}",
        starts_at=existing.granted_at,
    )
    db.flush()
    return existing


def revoke_lifetime_access_for_purchase(db: Session, purchase: Purchase) -> CreatorLifetimeAccess | None:
    row = db.scalar(
        select(CreatorLifetimeAccess).where(
            CreatorLifetimeAccess.purchase_id == purchase.id,
            CreatorLifetimeAccess.user_id == purchase.user_id,
            CreatorLifetimeAccess.hosted_book_id == purchase.hosted_book_id,
        )
    )
    if row is None or row.status != "active":
        return row

    row.status = "revoked"
    row.revoked_at = _now()
    revoke_book_entitlement(
        db,
        user_id=row.user_id,
        book_id=row.hosted_book.book_id,
        source="lifetime_access",
        source_reference=f"creator_lifetime_access:{row.id}",
    )
    db.flush()
    return row
