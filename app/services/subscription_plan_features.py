from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subscription_plan_feature import SubscriptionPlanFeatureLimit


def normalize_feature_key(feature_key: str) -> str:
    normalized = feature_key.strip().lower()
    if not normalized or not normalized.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid feature key")
    return normalized


def get_plan_feature_limit(
    db: Session,
    *,
    plan_id: int,
    feature_key: str,
) -> SubscriptionPlanFeatureLimit | None:
    """Resolve one feature configuration from a plan catalogue entry.

    This does not resolve a user's subscription and does not grant access.
    """
    normalized = normalize_feature_key(feature_key)
    return db.scalar(
        select(SubscriptionPlanFeatureLimit).where(
            SubscriptionPlanFeatureLimit.plan_id == plan_id,
            SubscriptionPlanFeatureLimit.feature_key == normalized,
        )
    )
