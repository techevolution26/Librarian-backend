from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.creator_account import CreatorAccount
from app.models.user import User
from app.schemas.creator_payout import (
    CreatorPayoutBalance,
    CreatorPayoutFailure,
    CreatorPayoutOverview,
    CreatorPayoutProviderUpdate,
    CreatorPayoutRead,
    CreatorPayoutRequest,
)
from app.services.creator_payout import (
    approve_creator_payout,
    begin_creator_payout,
    cancel_creator_payout,
    complete_creator_payout,
    fail_creator_payout,
    get_creator_payout_balances,
    list_creator_payouts,
    request_creator_payout,
)

router = APIRouter(prefix="/creator/payouts", tags=["creator-payouts"])


def _owned_account(db: Session, user_id: int) -> CreatorAccount:
    account = db.scalar(select(CreatorAccount).where(CreatorAccount.user_id == user_id))
    if account is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Creator account not found")
    return account


def _read_overview(db: Session, creator_account_id: int) -> CreatorPayoutOverview:
    balances = [CreatorPayoutBalance(**row) for row in get_creator_payout_balances(db, creator_account_id)]
    return CreatorPayoutOverview(balances=balances, payouts=list_creator_payouts(db, creator_account_id))


@router.get("/overview", response_model=CreatorPayoutOverview)
def get_payout_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorPayoutOverview:
    account = _owned_account(db, current_user.id)
    return _read_overview(db, account.id)


@router.post("", response_model=CreatorPayoutRead, status_code=status.HTTP_201_CREATED)
def create_payout_request(
    payload: CreatorPayoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorPayoutRead:
    account = _owned_account(db, current_user.id)
    return request_creator_payout(
        db,
        creator_account_id=account.id,
        currency=payload.currency,
        amount_minor=payload.amount_minor,
        idempotency_key=payload.idempotency_key,
    )


@router.post("/admin/{payout_id}/approve", response_model=CreatorPayoutRead)
def approve_payout(
    payout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorPayoutRead:
    require_admin_user(current_user)
    return approve_creator_payout(db, payout_id)


@router.post("/admin/{payout_id}/process", response_model=CreatorPayoutRead)
def process_payout(
    payout_id: int,
    payload: CreatorPayoutProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorPayoutRead:
    require_admin_user(current_user)
    return begin_creator_payout(db, payout_id, payload.provider)


@router.post("/admin/{payout_id}/complete", response_model=CreatorPayoutRead)
def complete_payout(
    payout_id: int,
    payload: CreatorPayoutProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorPayoutRead:
    require_admin_user(current_user)
    return complete_creator_payout(
        db,
        payout_id,
        provider_payout_id=payload.provider_payout_id,
        provider_reference=payload.provider_reference,
    )


@router.post("/admin/{payout_id}/fail", response_model=CreatorPayoutRead)
def fail_payout(
    payout_id: int,
    payload: CreatorPayoutFailure,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorPayoutRead:
    require_admin_user(current_user)
    return fail_creator_payout(db, payout_id, payload.failure_code, payload.failure_message)


@router.post("/admin/{payout_id}/retry", response_model=CreatorPayoutRead)
def retry_payout(
    payout_id: int,
    payload: CreatorPayoutProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorPayoutRead:
    require_admin_user(current_user)
    return begin_creator_payout(db, payout_id, payload.provider)


@router.post("/admin/{payout_id}/cancel", response_model=CreatorPayoutRead)
def cancel_payout(
    payout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorPayoutRead:
    require_admin_user(current_user)
    return cancel_creator_payout(db, payout_id)
