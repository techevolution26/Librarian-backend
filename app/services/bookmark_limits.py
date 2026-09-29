from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bookmark import Bookmark
from app.models.subscription_plan_feature import SubscriptionPlanFeatureLimit
from app.services.subscription_plan_features import normalize_feature_key

BOOKMARK_COUNT_FEATURE_KEY = "bookmark_count"


def get_bookmark_count(db: Session, *, user_id: int) -> int:
    """Return the user's current bookmark count."""
    return int(
        db.scalar(
            select(func.count(Bookmark.id)).where(Bookmark.user_id == user_id)
        )
        or 0
    )


def get_bookmark_limit_for_plan(
    db: Session,
    *,
    plan_id: int,
) -> SubscriptionPlanFeatureLimit | None:
    """Resolve the bookmark-count configuration for a catalogue plan.

    ``None`` means the plan has no explicit bookmark policy. It does not
    imply unlimited access; the subscription/entitlement layer must decide
    the effective plan before enforcement is applied.
    """
    return db.scalar(
        select(SubscriptionPlanFeatureLimit).where(
            SubscriptionPlanFeatureLimit.plan_id == plan_id,
            SubscriptionPlanFeatureLimit.feature_key == normalize_feature_key(
                BOOKMARK_COUNT_FEATURE_KEY
            ),
        )
    )


def bookmark_limit_allows_creation(
    db: Session,
    *,
    user_id: int,
    plan_id: int,
) -> tuple[bool, int, int | None]:
    """Evaluate whether another bookmark fits a specific plan's limit.

    This is deliberately plan-scoped rather than user-plan-scoped. T4 does
    not invent subscription ownership; T7 will provide the effective plan.
    """
    current_count = get_bookmark_count(db, user_id=user_id)
    configuration = get_bookmark_limit_for_plan(db, plan_id=plan_id)

    if configuration is None or not configuration.enabled:
        return False, current_count, 0

    if configuration.limit_value is None:
        return True, current_count, None

    return current_count < configuration.limit_value, current_count, configuration.limit_value
