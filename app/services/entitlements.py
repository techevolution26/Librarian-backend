from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.creator_hosted_book import CreatorHostedBook
from app.models.creator_paid_book import CreatorPaidBook
from app.models.entitlement import Entitlement


def _now() -> datetime:
    return datetime.now(timezone.utc)


def grant_book_entitlement(
    db: Session,
    *,
    user_id: int,
    book_id: int,
    source: str,
    source_reference: str,
    starts_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> Entitlement:
    """Create or reactivate the authoritative book-access entitlement."""
    existing = db.scalar(
        select(Entitlement).where(
            Entitlement.user_id == user_id,
            Entitlement.entitlement_type == "book_access",
            Entitlement.book_id == book_id,
            Entitlement.source == source,
            Entitlement.source_reference == source_reference,
        )
    )
    start = starts_at or _now()
    if existing is not None:
        existing.status = "active"
        existing.starts_at = start
        existing.expires_at = expires_at
        existing.revoked_at = None
        db.flush()
        return existing

    row = Entitlement(
        user_id=user_id,
        entitlement_type="book_access",
        book_id=book_id,
        source=source,
        source_reference=source_reference,
        status="active",
        starts_at=start,
        expires_at=expires_at,
    )
    db.add(row)
    db.flush()
    return row


def revoke_book_entitlement(
    db: Session,
    *,
    user_id: int,
    book_id: int,
    source: str,
    source_reference: str,
) -> Entitlement | None:
    row = db.scalar(
        select(Entitlement).where(
            Entitlement.user_id == user_id,
            Entitlement.entitlement_type == "book_access",
            Entitlement.book_id == book_id,
            Entitlement.source == source,
            Entitlement.source_reference == source_reference,
        )
    )
    if row is not None and row.status == "active":
        row.status = "revoked"
        row.revoked_at = _now()
        db.flush()
    return row


def resolve_book_access(db: Session, *, user_id: int, book_id: int) -> tuple[bool, str, Entitlement | None]:
    """Return the single access decision used by protected book workflows.

    Published, non-archived books are public. Non-public books require an
    active, time-valid book entitlement.
    """
    book = db.get(Book, book_id)
    if book is None:
        return False, "book_not_found", None
    if book.archived_at is not None:
        return False, "book_archived", None

    active_paid_offer = db.scalar(
        select(CreatorPaidBook.id)
        .join(CreatorHostedBook, CreatorHostedBook.id == CreatorPaidBook.hosted_book_id)
        .where(
            CreatorHostedBook.book_id == book.id,
            CreatorHostedBook.status == "hosted",
            CreatorPaidBook.status == "active",
        )
    )
    if book.visibility == "published" and active_paid_offer is None:
        return True, "public", None

    now = _now()
    entitlement = db.scalar(
        select(Entitlement)
        .where(
            Entitlement.user_id == user_id,
            Entitlement.entitlement_type == "book_access",
            Entitlement.book_id == book_id,
            Entitlement.status == "active",
            Entitlement.starts_at <= now,
            (Entitlement.expires_at.is_(None) | (Entitlement.expires_at > now)),
        )
        .order_by(Entitlement.expires_at.is_(None).desc(), Entitlement.id.desc())
    )
    if entitlement is not None:
        return True, "entitled", entitlement

    return False, "entitlement_required", None
