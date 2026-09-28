from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.creator_account import CreatorAccount
from app.models.user import User
from app.schemas.creator_revenue import CreatorRevenueLedgerEntryRead, CreatorRevenueRecordCreate, CreatorRevenueSummary
from app.services.creator_revenue import build_creator_revenue_summary, record_verified_revenue_event

router = APIRouter(prefix="/creator/revenue", tags=["creator-revenue"] )


def _owned_account(db: Session, user_id: int) -> CreatorAccount:
    account = db.scalar(select(CreatorAccount).where(CreatorAccount.user_id == user_id))
    if account is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Creator account not found")
    return account


@router.get("/summary", response_model=CreatorRevenueSummary)
def get_revenue_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorRevenueSummary:
    account = _owned_account(db, current_user.id)
    return build_creator_revenue_summary(db, account.id)


@router.post("/admin/record", response_model=CreatorRevenueLedgerEntryRead, status_code=status.HTTP_201_CREATED)
def record_revenue_event(
    payload: CreatorRevenueRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorRevenueLedgerEntryRead:
    require_admin_user(current_user)
    return record_verified_revenue_event(db, payload)
