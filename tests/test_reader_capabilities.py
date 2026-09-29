from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription_plan_feature import SubscriptionPlanFeatureLimit
from app.services.reader_capabilities import (
    ADVANCED_READER_CAPABILITIES,
    get_active_plan_for_reader_capabilities,
    get_advanced_reader_capability,
    list_advanced_reader_capabilities,
)


def make_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[SubscriptionPlan.__table__, SubscriptionPlanFeatureLimit.__table__],
    )
    return engine


def make_plan(db: Session, *, code: str = "reader", status: str = "active") -> SubscriptionPlan:
    plan = SubscriptionPlan(
        code=code,
        name="Reader",
        description="",
        price_amount_minor=0,
        currency="usd",
        billing_interval="none",
        status=status,
        sort_order=1,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def test_advanced_reader_capability_vocabulary_is_explicit():
    assert ADVANCED_READER_CAPABILITIES == {"advanced_reader"}


def test_capability_lookup_resolves_plan_catalogue_configuration():
    engine = make_db()
    with Session(engine) as db:
        plan = make_plan(db)
        db.add(SubscriptionPlanFeatureLimit(
            plan_id=plan.id,
            feature_key="advanced_reader",
            enabled=True,
            limit_value=None,
        ))
        db.commit()
        row = get_advanced_reader_capability(db, plan_id=plan.id)
        assert row is not None
        assert row.enabled is True
        assert row.limit_value is None


def test_unknown_capability_is_rejected():
    engine = make_db()
    with Session(engine) as db:
        plan = make_plan(db)
        try:
            get_advanced_reader_capability(db, plan_id=plan.id, capability="invented_capability")
        except ValueError as exc:
            assert "Unknown advanced reader capability" in str(exc)
        else:
            raise AssertionError("unknown reader capabilities must be rejected")


def test_list_returns_only_advanced_reader_capabilities():
    engine = make_db()
    with Session(engine) as db:
        plan = make_plan(db)
        db.add_all([
            SubscriptionPlanFeatureLimit(plan_id=plan.id, feature_key="advanced_reader", enabled=True),
            SubscriptionPlanFeatureLimit(plan_id=plan.id, feature_key="bookmark_count", enabled=True, limit_value=10),
        ])
        db.commit()
        rows = list_advanced_reader_capabilities(db, plan_id=plan.id)
        assert [row.feature_key for row in rows] == ["advanced_reader"]


def test_active_plan_lookup_excludes_draft_and_archived_plans():
    engine = make_db()
    with Session(engine) as db:
        make_plan(db, code="draft-plan", status="draft")
        make_plan(db, code="archived-plan", status="archived")
        active = make_plan(db, code="active-plan", status="active")
        assert get_active_plan_for_reader_capabilities(db, plan_code="DRAFT-PLAN") is None
        assert get_active_plan_for_reader_capabilities(db, plan_code="archived-plan") is None
        resolved = get_active_plan_for_reader_capabilities(db, plan_code="ACTIVE-PLAN")
        assert resolved is not None
        assert resolved.id == active.id


def test_capability_resolution_does_not_require_user_entitlement():
    engine = make_db()
    with Session(engine) as db:
        plan = make_plan(db)
        db.add(SubscriptionPlanFeatureLimit(
            plan_id=plan.id,
            feature_key="advanced_reader",
            enabled=False,
            limit_value=None,
        ))
        db.commit()
        row = get_advanced_reader_capability(db, plan_id=plan.id)
        assert row is not None
        assert row.enabled is False
