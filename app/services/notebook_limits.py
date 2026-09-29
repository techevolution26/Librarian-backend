from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.note import Note
from app.models.subscription_plan_feature import SubscriptionPlanFeatureLimit
from app.services.subscription_plan_features import normalize_feature_key

NOTEBOOK_NOTE_COUNT_FEATURE_KEY = "notebook_note_count"


def get_notebook_note_count(db: Session, *, user_id: int) -> int:
    """Return the number of private notes owned by the user's notebook."""
    return int(
        db.scalar(
            select(func.count(Note.id))
            .join(Note.notebook)
            .where(Note.notebook.has(user_id=user_id))
        )
        or 0
    )


def get_notebook_note_limit_for_plan(
    db: Session,
    *,
    plan_id: int,
) -> SubscriptionPlanFeatureLimit | None:
    """Resolve notebook-note capacity for one catalogue plan.

    ``None`` means no explicit notebook-note policy exists for the plan. It
    does not imply unlimited access; the future subscription layer must first
    resolve the user's effective plan.
    """
    return db.scalar(
        select(SubscriptionPlanFeatureLimit).where(
            SubscriptionPlanFeatureLimit.plan_id == plan_id,
            SubscriptionPlanFeatureLimit.feature_key == normalize_feature_key(
                NOTEBOOK_NOTE_COUNT_FEATURE_KEY
            ),
        )
    )


def notebook_limit_allows_note_creation(
    db: Session,
    *,
    user_id: int,
    plan_id: int,
) -> tuple[bool, int, int | None]:
    """Evaluate whether another private notebook note fits a plan's limit."""
    current_count = get_notebook_note_count(db, user_id=user_id)
    configuration = get_notebook_note_limit_for_plan(db, plan_id=plan_id)

    if configuration is None or not configuration.enabled:
        return False, current_count, 0

    if configuration.limit_value is None:
        return True, current_count, None

    return current_count < configuration.limit_value, current_count, configuration.limit_value
