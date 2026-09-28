from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.creator_account import CreatorAccount
from app.models.creator_hosted_book import CreatorHostedBook
from app.models.creator_paid_book import CreatorPaidBook
from app.models.creator_rights_declaration import CreatorRightsDeclaration
from app.models.user import User
from app.schemas.creator_paid_book import CreatorPaidBookCreate, CreatorPaidBookRead, CreatorPaidBookUpdate

router = APIRouter(prefix="/creator/hosted-books", tags=["creator-paid-books"])


def _owned_hosted_book(db: Session, hosted_book_id: int, user_id: int) -> CreatorHostedBook:
    row = db.scalar(
        select(CreatorHostedBook)
        .join(CreatorAccount, CreatorAccount.id == CreatorHostedBook.creator_account_id)
        .where(CreatorHostedBook.id == hosted_book_id, CreatorAccount.user_id == user_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Hosted book not found")
    return row


def _commercial_rights(db: Session, submission_id: int) -> CreatorRightsDeclaration:
    rights = db.scalar(
        select(CreatorRightsDeclaration)
        .where(
            CreatorRightsDeclaration.submission_id == submission_id,
            CreatorRightsDeclaration.status == "active",
        )
        .order_by(CreatorRightsDeclaration.version.desc())
    )
    if rights is None:
        raise HTTPException(status_code=409, detail="An active rights declaration is required before selling this book")
    if not rights.hosting_allowed:
        raise HTTPException(status_code=409, detail="The active rights declaration does not allow hosting")
    if not rights.commercial_use_allowed:
        raise HTTPException(status_code=409, detail="The active rights declaration does not allow commercial use")
    return rights


@router.get("/{hosted_book_id}/paid-offer", response_model=CreatorPaidBookRead | None)
def get_paid_offer(
    hosted_book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorPaidBookRead | None:
    hosted = _owned_hosted_book(db, hosted_book_id, current_user.id)
    return db.scalar(select(CreatorPaidBook).where(CreatorPaidBook.hosted_book_id == hosted.id))


@router.post("/{hosted_book_id}/paid-offer", response_model=CreatorPaidBookRead, status_code=status.HTTP_201_CREATED)
def create_paid_offer(
    hosted_book_id: int,
    payload: CreatorPaidBookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorPaidBookRead:
    hosted = _owned_hosted_book(db, hosted_book_id, current_user.id)
    if hosted.creator_account.status != "active":
        raise HTTPException(status_code=403, detail="Suspended creator accounts cannot sell books")
    if hosted.status != "hosted":
        raise HTTPException(status_code=409, detail="A hosted file is required before creating a paid offer")
    _commercial_rights(db, hosted.submission_id)

    existing = db.scalar(select(CreatorPaidBook).where(CreatorPaidBook.hosted_book_id == hosted.id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="A paid offer already exists for this hosted book")

    offer = CreatorPaidBook(
        hosted_book_id=hosted.id,
        creator_account_id=hosted.creator_account_id,
        price_amount_minor=payload.price_amount_minor,
        currency=payload.currency,
        status=payload.status,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


@router.patch("/{hosted_book_id}/paid-offer", response_model=CreatorPaidBookRead)
def update_paid_offer(
    hosted_book_id: int,
    payload: CreatorPaidBookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorPaidBookRead:
    hosted = _owned_hosted_book(db, hosted_book_id, current_user.id)
    offer = db.scalar(select(CreatorPaidBook).where(CreatorPaidBook.hosted_book_id == hosted.id))
    if offer is None:
        raise HTTPException(status_code=404, detail="Paid offer not found")

    if offer.status == "archived" and payload.model_fields_set & {"price_amount_minor", "currency"}:
        raise HTTPException(status_code=409, detail="Archived paid offers cannot be repriced")

    if payload.model_fields_set & {"price_amount_minor", "currency", "status"} and offer.status != "archived":
        _commercial_rights(db, hosted.submission_id)

    if "price_amount_minor" in payload.model_fields_set and payload.price_amount_minor is not None:
        offer.price_amount_minor = payload.price_amount_minor
    if "currency" in payload.model_fields_set and payload.currency is not None:
        offer.currency = payload.currency
    if "status" in payload.model_fields_set and payload.status is not None:
        if payload.status == "active":
            if hosted.status != "hosted":
                raise HTTPException(status_code=409, detail="A hosted file is required before activating a paid offer")
            _commercial_rights(db, hosted.submission_id)
        offer.status = payload.status

    db.commit()
    db.refresh(offer)
    return offer
