from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription_plan_feature import SubscriptionPlanFeatureLimit
from app.services.subscription_plan_features import get_plan_feature_limit

ADVANCED_READER_CAPABILITIES = {
    "advanced_reader",
}


def get_advanced_reader_capability(
    db: Session,
    *,
    plan_id: int,
    capability: str = "advanced_reader",
) -> SubscriptionPlanFeatureLimit | None:
    """Resolve one advanced-reader capability from plan catalogue metadata.

    This intentionally does not resolve a user's subscription, entitlement,
    or billing state. It only describes what a plan is configured to expose.
    """
    normalized = capability.strip().lower()
    if normalized not in ADVANCED_READER_CAPABILITIES:
        raise ValueError("Unknown advanced reader capability")
    return get_plan_feature_limit(db, plan_id=plan_id, feature_key=normalized)


def list_advanced_reader_capabilities(
    db: Session,
    *,
    plan_id: int,
) -> list[SubscriptionPlanFeatureLimit]:
    """Return configured advanced-reader capabilities for one plan."""
    return list(
        db.scalars(
            select(SubscriptionPlanFeatureLimit)
            .where(
                SubscriptionPlanFeatureLimit.plan_id == plan_id,
                SubscriptionPlanFeatureLimit.feature_key.in_(ADVANCED_READER_CAPABILITIES),
            )
            .order_by(SubscriptionPlanFeatureLimit.feature_key.asc())
        ).all()
    )


def get_active_plan_for_reader_capabilities(
    db: Session,
    *,
    plan_code: str,
) -> SubscriptionPlan | None:
    """Resolve an active catalogue plan by code for capability discovery."""
    normalized = plan_code.strip().lower()
    return db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.code == normalized,
            SubscriptionPlan.status == "active",
        )
    )
