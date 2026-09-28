from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.creator_hosted_book import CreatorHostedBook
from app.models.creator_lifetime_access import (
    CREATOR_LIFETIME_ACCESS_SOURCES,
    CreatorLifetimeAccess,
)
from app.models.creator_paid_book import CreatorPaidBook
from app.models.user import User
from app.schemas.creator_lifetime_access import CreatorLifetimeAccessRead

router = APIRouter(prefix="/lifetime-access", tags=["lifetime-access"])


def _read(row: CreatorLifetimeAccess) -> CreatorLifetimeAccessRead:
    book = row.hosted_book.book
    return CreatorLifetimeAccessRead(
        id=row.id,
        user_id=row.user_id,
        hosted_book_id=row.hosted_book_id,
        paid_offer_id=row.paid_offer_id,
        status=row.status,
        access_source=row.access_source,
        granted_at=row.granted_at,
        revoked_at=row.revoked_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        title=book.title,
        author_name=book.author,
        book_id=book.id,
    )


@router.get("/mine", response_model=list[CreatorLifetimeAccessRead])
def list_my_lifetime_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CreatorLifetimeAccessRead]:
    rows = db.scalars(
        select(CreatorLifetimeAccess)
        .where(CreatorLifetimeAccess.user_id == current_user.id, CreatorLifetimeAccess.status == "active")
        .join(CreatorHostedBook, CreatorHostedBook.id == CreatorLifetimeAccess.hosted_book_id)
        .order_by(CreatorLifetimeAccess.granted_at.desc())
    ).all()
    return [_read(row) for row in rows]


@router.get("/books/{hosted_book_id}", response_model=CreatorLifetimeAccessRead | None)
def get_my_lifetime_access(
    hosted_book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorLifetimeAccessRead | None:
    row = db.scalar(
        select(CreatorLifetimeAccess)
        .where(
            CreatorLifetimeAccess.user_id == current_user.id,
            CreatorLifetimeAccess.hosted_book_id == hosted_book_id,
            CreatorLifetimeAccess.status == "active",
        )
    )
    return _read(row) if row else None


@router.post("/admin/grant", response_model=CreatorLifetimeAccessRead, status_code=status.HTTP_201_CREATED)
def admin_grant_lifetime_access(
    user_id: int,
    hosted_book_id: int,
    paid_offer_id: int | None = None,
    access_source: str = "admin",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorLifetimeAccessRead:
    require_admin_user(current_user)
    if access_source not in CREATOR_LIFETIME_ACCESS_SOURCES:
        raise HTTPException(status_code=422, detail="Invalid lifetime access source")

    user = db.get(User, user_id)
    hosted = db.get(CreatorHostedBook, hosted_book_id)
    if user is None or hosted is None:
        raise HTTPException(status_code=404, detail="User or hosted book not found")
    if hosted.status != "hosted":
        raise HTTPException(status_code=409, detail="The hosted book must have an active hosted file")

    offer = None
    if paid_offer_id is not None:
        offer = db.get(CreatorPaidBook, paid_offer_id)
        if offer is None or offer.hosted_book_id != hosted.id:
            raise HTTPException(status_code=409, detail="The paid offer does not belong to this hosted book")

    existing = db.scalar(
        select(CreatorLifetimeAccess).where(
            CreatorLifetimeAccess.user_id == user_id,
            CreatorLifetimeAccess.hosted_book_id == hosted_book_id,
        )
    )
    now = datetime.now(timezone.utc)
    if existing is not None:
        if existing.status == "active":
            return _read(existing)
        existing.status = "active"
        existing.revoked_at = None
        existing.granted_at = now
        existing.paid_offer_id = paid_offer_id
        existing.access_source = access_source
        db.commit()
        db.refresh(existing)
        return _read(existing)

    row = CreatorLifetimeAccess(
        user_id=user_id,
        hosted_book_id=hosted_book_id,
        paid_offer_id=paid_offer_id,
        status="active",
        access_source=access_source,
        granted_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/{access_id}/admin-revoke", response_model=CreatorLifetimeAccessRead)
def admin_revoke_lifetime_access(
    access_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorLifetimeAccessRead:
    require_admin_user(current_user)
    row = db.get(CreatorLifetimeAccess, access_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Lifetime access not found")
    if row.status == "active":
        row.status = "revoked"
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
    return _read(row)
