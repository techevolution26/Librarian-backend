from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.authz import require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.schemas.subscription_plan import SubscriptionPlanCreate, SubscriptionPlanRead, SubscriptionPlanUpdate

router = APIRouter(prefix="/plans", tags=["subscription-plans"])


def _read(row: SubscriptionPlan) -> SubscriptionPlanRead:
    return SubscriptionPlanRead.model_validate(row)


@router.get("", response_model=list[SubscriptionPlanRead])
def list_public_plans(
    db: Session = Depends(get_db),
) -> list[SubscriptionPlanRead]:
    rows = db.scalars(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.status == "active")
        .order_by(SubscriptionPlan.sort_order.asc(), SubscriptionPlan.id.asc())
    ).all()
    return [_read(row) for row in rows]


@router.get("/{code}", response_model=SubscriptionPlanRead)
def get_public_plan(
    code: str,
    db: Session = Depends(get_db),
) -> SubscriptionPlanRead:
    row = db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.code == code.strip().lower(),
            SubscriptionPlan.status == "active",
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _read(row)


@router.get("/admin/all", response_model=list[SubscriptionPlanRead])
def list_all_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SubscriptionPlanRead]:
    require_admin_user(current_user)
    rows = db.scalars(
        select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order.asc(), SubscriptionPlan.id.asc())
    ).all()
    return [_read(row) for row in rows]


@router.post("/admin", response_model=SubscriptionPlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: SubscriptionPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionPlanRead:
    require_admin_user(current_user)
    if payload.price_amount_minor == 0 and payload.billing_interval != "none":
        raise HTTPException(status_code=422, detail="A zero-price plan must use billing interval none")
    if payload.price_amount_minor > 0 and payload.billing_interval == "none":
        raise HTTPException(status_code=422, detail="A paid plan must specify a billing interval")

    row = SubscriptionPlan(**payload.model_dump())
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A plan with this code already exists") from exc
    db.refresh(row)
    return _read(row)


@router.patch("/admin/{plan_id}", response_model=SubscriptionPlanRead)
def update_plan(
    plan_id: int,
    payload: SubscriptionPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionPlanRead:
    require_admin_user(current_user)
    row = db.get(SubscriptionPlan, plan_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    values = payload.model_dump(exclude_unset=True)
    price = values.get("price_amount_minor", row.price_amount_minor)
    interval = values.get("billing_interval", row.billing_interval)
    if price == 0 and interval != "none":
        raise HTTPException(status_code=422, detail="A zero-price plan must use billing interval none")
    if price > 0 and interval == "none":
        raise HTTPException(status_code=422, detail="A paid plan must specify a billing interval")

    for key, value in values.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _read(row)
