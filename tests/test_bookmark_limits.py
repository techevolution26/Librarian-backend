from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.bookmark import Bookmark
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription_plan_feature import SubscriptionPlanFeatureLimit
from app.models.user import User
from app.services.bookmark_limits import (
    BOOKMARK_COUNT_FEATURE_KEY,
    bookmark_limit_allows_creation,
    get_bookmark_count,
    get_bookmark_limit_for_plan,
)


def make_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            SubscriptionPlan.__table__,
            SubscriptionPlanFeatureLimit.__table__,
            Bookmark.__table__,
        ],
    )
    return engine


def test_bookmark_feature_key_is_explicit():
    assert BOOKMARK_COUNT_FEATURE_KEY == "bookmark_count"


def test_bookmark_count_starts_at_zero():
    engine = make_db()
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        assert get_bookmark_count(db, user_id=user.id) == 0


def test_bookmark_count_counts_only_owned_rows():
    engine = make_db()
    with Session(engine) as db:
        first = User(full_name="First", email="first@example.com", password_hash="x")
        second = User(full_name="Second", email="second@example.com", password_hash="x")
        db.add_all([first, second])
        db.commit()
        db.refresh(first)
        db.refresh(second)
        db.add_all([
            Bookmark(user_id=first.id, book_id=1, title="One"),
            Bookmark(user_id=first.id, book_id=2, title="Two"),
            Bookmark(user_id=second.id, book_id=3, title="Other"),
        ])
        db.commit()
        assert get_bookmark_count(db, user_id=first.id) == 2
        assert get_bookmark_count(db, user_id=second.id) == 1


def test_missing_plan_feature_does_not_become_unlimited():
    engine = make_db()
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        plan = SubscriptionPlan(
            code="reader",
            name="Reader",
            description="Reader plan",
            price_amount_minor=0,
            currency="usd",
            billing_interval="none",
            status="active",
            sort_order=1,
        )
        db.add_all([user, plan])
        db.commit()
        db.refresh(user)
        db.refresh(plan)
        allowed, count, limit = bookmark_limit_allows_creation(
            db, user_id=user.id, plan_id=plan.id
        )
        assert allowed is False
        assert count == 0
        assert limit == 0


def test_disabled_bookmark_feature_denies_creation():
    engine = make_db()
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        plan = SubscriptionPlan(
            code="no-bookmarks",
            name="No Bookmarks",
            description="",
            price_amount_minor=0,
            currency="usd",
            billing_interval="none",
            status="active",
            sort_order=1,
        )
        db.add_all([user, plan])
        db.commit()
        db.refresh(user)
        db.refresh(plan)
        db.add(SubscriptionPlanFeatureLimit(
            plan_id=plan.id,
            feature_key=BOOKMARK_COUNT_FEATURE_KEY,
            enabled=False,
            limit_value=None,
        ))
        db.commit()
        allowed, count, limit = bookmark_limit_allows_creation(
            db, user_id=user.id, plan_id=plan.id
        )
        assert allowed is False
        assert count == 0
        assert limit == 0


def test_numeric_bookmark_limit_blocks_at_ceiling():
    engine = make_db()
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        plan = SubscriptionPlan(
            code="limited",
            name="Limited",
            description="",
            price_amount_minor=0,
            currency="usd",
            billing_interval="none",
            status="active",
            sort_order=1,
        )
        db.add_all([user, plan])
        db.commit()
        db.refresh(user)
        db.refresh(plan)
        db.add(SubscriptionPlanFeatureLimit(
            plan_id=plan.id,
            feature_key=BOOKMARK_COUNT_FEATURE_KEY,
            enabled=True,
            limit_value=2,
        ))
        db.add_all([
            Bookmark(user_id=user.id, book_id=1, title="One"),
            Bookmark(user_id=user.id, book_id=2, title="Two"),
        ])
        db.commit()
        allowed, count, limit = bookmark_limit_allows_creation(
            db, user_id=user.id, plan_id=plan.id
        )
        assert allowed is False
        assert count == 2
        assert limit == 2


def test_numeric_bookmark_limit_allows_below_ceiling():
    engine = make_db()
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        plan = SubscriptionPlan(
            code="limited-two",
            name="Limited Two",
            description="",
            price_amount_minor=0,
            currency="usd",
            billing_interval="none",
            status="active",
            sort_order=1,
        )
        db.add_all([user, plan])
        db.commit()
        db.refresh(user)
        db.refresh(plan)
        db.add(SubscriptionPlanFeatureLimit(
            plan_id=plan.id,
            feature_key=BOOKMARK_COUNT_FEATURE_KEY,
            enabled=True,
            limit_value=2,
        ))
        db.add(Bookmark(user_id=user.id, book_id=1, title="One"))
        db.commit()
        allowed, count, limit = bookmark_limit_allows_creation(
            db, user_id=user.id, plan_id=plan.id
        )
        assert allowed is True
        assert count == 1
        assert limit == 2


def test_unlimited_bookmark_feature_allows_creation():
    engine = make_db()
    with Session(engine) as db:
        user = User(full_name="Reader", email="reader@example.com", password_hash="x")
        plan = SubscriptionPlan(
            code="unlimited",
            name="Unlimited",
            description="",
            price_amount_minor=100,
            currency="usd",
            billing_interval="month",
            status="active",
            sort_order=1,
        )
        db.add_all([user, plan])
        db.commit()
        db.refresh(user)
        db.refresh(plan)
        db.add(SubscriptionPlanFeatureLimit(
            plan_id=plan.id,
            feature_key=BOOKMARK_COUNT_FEATURE_KEY,
            enabled=True,
            limit_value=None,
        ))
        db.commit()
        allowed, count, limit = bookmark_limit_allows_creation(
            db, user_id=user.id, plan_id=plan.id
        )
        assert allowed is True
        assert count == 0
        assert limit is None


def test_limit_lookup_uses_bookmark_count_key():
    engine = make_db()
    with Session(engine) as db:
        plan = SubscriptionPlan(
            code="lookup",
            name="Lookup",
            description="",
            price_amount_minor=0,
            currency="usd",
            billing_interval="none",
            status="active",
            sort_order=1,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        feature = SubscriptionPlanFeatureLimit(
            plan_id=plan.id,
            feature_key=BOOKMARK_COUNT_FEATURE_KEY,
            enabled=True,
            limit_value=25,
        )
        db.add(feature)
        db.commit()
        resolved = get_bookmark_limit_for_plan(db, plan_id=plan.id)
        assert resolved is not None
        assert resolved.limit_value == 25
