from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription_plan_feature import SubscriptionPlanFeatureLimit
from app.models.user import User
from app.schemas.subscription_plan_feature import SubscriptionPlanFeatureLimitRead, SubscriptionPlanFeatureLimitUpsert
from app.services.subscription_plan_features import normalize_feature_key

router = APIRouter(prefix="/plans/admin", tags=["subscription-plan-features"])


@router.put(
    "/{plan_id}/features/{feature_key}",
    response_model=SubscriptionPlanFeatureLimitRead,
)
def upsert_plan_feature_limit(
    plan_id: int,
    feature_key: str,
    payload: SubscriptionPlanFeatureLimitUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionPlanFeatureLimitRead:
    require_admin_user(current_user)
    plan = db.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    normalized_path_key = normalize_feature_key(feature_key)
    normalized_body_key = normalize_feature_key(payload.feature_key)
    if normalized_path_key != normalized_body_key:
        raise HTTPException(status_code=422, detail="Feature key in path and body must match")

    row = db.scalar(
        select(SubscriptionPlanFeatureLimit).where(
            SubscriptionPlanFeatureLimit.plan_id == plan_id,
            SubscriptionPlanFeatureLimit.feature_key == normalized_path_key,
        )
    )
    if row is None:
        row = SubscriptionPlanFeatureLimit(
            plan_id=plan_id,
            feature_key=normalized_path_key,
            enabled=payload.enabled,
            limit_value=payload.limit_value,
        )
        db.add(row)
    else:
        row.enabled = payload.enabled
        row.limit_value = payload.limit_value

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Feature limit already exists for this plan") from exc
    db.refresh(row)
    return SubscriptionPlanFeatureLimitRead.model_validate(row)


@router.delete(
    "/{plan_id}/features/{feature_key}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_plan_feature_limit(
    plan_id: int,
    feature_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    require_admin_user(current_user)
    row = db.scalar(
        select(SubscriptionPlanFeatureLimit).where(
            SubscriptionPlanFeatureLimit.plan_id == plan_id,
            SubscriptionPlanFeatureLimit.feature_key == normalize_feature_key(feature_key),
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Feature limit not found")
    db.delete(row)
    db.commit()
