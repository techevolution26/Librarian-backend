from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.creator_account import CreatorAccount
from app.models.user import User
from app.schemas.creator import CreatorAccountCreate, CreatorAccountRead, CreatorAccountUpdate, CreatorDashboardRead
from app.schemas.creator_analytics import CreatorAnalyticsRead
from app.services.creator import build_creator_dashboard
from app.services.creator_analytics import build_creator_analytics

router = APIRouter(prefix="/creator", tags=["creator"])


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
