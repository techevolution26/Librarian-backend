from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.creator_account import CreatorAccount
from app.models.creator_hosted_book import CreatorHostedBook
from app.models.creator_paid_book import CreatorPaidBook
from app.models.book import Book
from app.models.user import User
from app.schemas.creator import (
    CreatorAccountCreate,
    CreatorAccountRead,
    CreatorAccountUpdate,
    CreatorDashboardRead,
    CreatorPublicBookRead,
    CreatorPublicProfileRead,
)
from app.schemas.creator_analytics import CreatorAnalyticsRead
from app.services.creator import build_creator_dashboard
from app.services.creator_analytics import build_creator_analytics

router = APIRouter(prefix="/creator", tags=["creator"])


@router.get("/public/{slug}", response_model=CreatorPublicProfileRead)
def get_public_creator_profile(
    slug: str,
    db: Session = Depends(get_db),
) -> CreatorPublicProfileRead:
    """Return the public creator identity and only explicitly published books.

    Private creators, suspended creators, archived books, and draft catalog
    records are intentionally indistinguishable from a missing profile.
    """
    account = db.scalar(
        select(CreatorAccount).where(
            CreatorAccount.slug == slug,
            CreatorAccount.is_public.is_(True),
            CreatorAccount.status == "active",
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Creator profile not found")

    rows = db.execute(
        select(Book, CreatorPaidBook)
        .join(CreatorHostedBook, CreatorHostedBook.book_id == Book.id)
        .outerjoin(
            CreatorPaidBook,
            (CreatorPaidBook.hosted_book_id == CreatorHostedBook.id)
            & (CreatorPaidBook.status == "active"),
        )
        .where(
            CreatorHostedBook.creator_account_id == account.id,
            CreatorHostedBook.status == "hosted",
            Book.visibility == "published",
            Book.archived_at.is_(None),
        )
        .order_by(Book.id.desc())
    ).all()

    return CreatorPublicProfileRead(
        display_name=account.display_name,
        slug=account.slug,
        bio=account.bio,
        website_url=account.website_url,
        profile_image_url=account.profile_image_url,
        books=[
            CreatorPublicBookRead(
                id=book.id,
                title=book.title,
                author=book.author,
                cover=book.cover,
                description=book.description,
                pages=book.pages,
                genre=book.genres,
                paid_offer_id=offer.id if offer else None,
                price_amount_minor=offer.price_amount_minor if offer else None,
                currency=offer.currency if offer else None,
            )
            for book, offer in rows
        ],
    )


def _get_owned_account(db: Session, user_id: int) -> CreatorAccount:
    account = db.scalar(select(CreatorAccount).where(CreatorAccount.user_id == user_id))
    if account is None:
        raise HTTPException(status_code=404, detail="Creator account not found")
    return account


def _ensure_slug_available(db: Session, slug: str, account_id: int | None = None) -> None:
    query = select(CreatorAccount).where(CreatorAccount.slug == slug)
    if account_id is not None:
        query = query.where(CreatorAccount.id != account_id)
    if db.scalar(query) is not None:
        raise HTTPException(status_code=409, detail="Creator slug is already in use")



@router.get("/me/public-url")
def get_my_public_creator_url(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    account = _get_owned_account(db, current_user.id)
    return {"slug": account.slug, "path": f"/creator/{account.slug}"}


@router.get("/dashboard", response_model=CreatorDashboardRead)
def get_creator_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorDashboardRead:
    account = _get_owned_account(db, current_user.id)
    return build_creator_dashboard(account)


@router.get("/analytics", response_model=CreatorAnalyticsRead)
def get_creator_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorAnalyticsRead:
    account = _get_owned_account(db, current_user.id)
    return build_creator_analytics(db, account.id)


@router.get("/me", response_model=CreatorAccountRead)
def get_my_creator_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorAccountRead:
    return _get_owned_account(db, current_user.id)


@router.post("/", response_model=CreatorAccountRead, status_code=status.HTTP_201_CREATED)
def create_creator_account(
    payload: CreatorAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorAccountRead:
    existing = db.scalar(select(CreatorAccount).where(CreatorAccount.user_id == current_user.id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Creator account already exists")

    _ensure_slug_available(db, payload.slug)
    account = CreatorAccount(
        user_id=current_user.id,
        display_name=payload.display_name.strip(),
        slug=payload.slug,
        bio=payload.bio.strip() if payload.bio else None,
        website_url=str(payload.website_url) if payload.website_url else None,
        profile_image_url=str(payload.profile_image_url) if payload.profile_image_url else None,
        is_public=payload.is_public,
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Creator account could not be created") from exc
    db.refresh(account)
    return account


@router.patch("/me", response_model=CreatorAccountRead)
def update_my_creator_account(
    payload: CreatorAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorAccountRead:
    account = _get_owned_account(db, current_user.id)

    if payload.slug is not None and payload.slug != account.slug:
        _ensure_slug_available(db, payload.slug, account.id)
        account.slug = payload.slug
    if payload.display_name is not None:
        account.display_name = payload.display_name.strip()
    if "bio" in payload.model_fields_set:
        account.bio = payload.bio.strip() if payload.bio else None
    if "website_url" in payload.model_fields_set:
        account.website_url = str(payload.website_url) if payload.website_url else None
    if "profile_image_url" in payload.model_fields_set:
        account.profile_image_url = str(payload.profile_image_url) if payload.profile_image_url else None
    if payload.is_public is not None:
        account.is_public = payload.is_public

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Creator account could not be updated") from exc
    db.refresh(account)
    return account
