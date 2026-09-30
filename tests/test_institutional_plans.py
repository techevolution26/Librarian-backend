from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from fastapi import HTTPException

from app.models.institution import Institution, InstitutionMembership, InstitutionSubscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.billing_customer import BillingCustomer
from app.models.subscription import Subscription
from app.models.user import User
from app.services.subscription_billing import get_effective_plan
from app.services.institution import (
    add_member,
    assign_plan,
    create_institution,
    get_effective_institution_subscription,
    get_active_plan_for_institution,
    revoke_member,
)



@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[
        User.__table__,
        SubscriptionPlan.__table__,
        Institution.__table__,
        InstitutionMembership.__table__,
        InstitutionSubscription.__table__,
        BillingCustomer.__table__,
        Subscription.__table__,
    ])
    with Session(engine) as session:
        yield session


def user(db, idx: int) -> User:
    row = User(full_name=f"User {idx}", email=f"u{idx}@example.test", password_hash="x")
    db.add(row)
    db.flush()
    return row


def plan(db, *, code="inst", seat_limit=None, plan_type="institutional") -> SubscriptionPlan:
    row = SubscriptionPlan(
        code=code,
        name=code.title(),
        description="",
        price_amount_minor=0,
        currency="usd",
        billing_interval="none",
        status="active",
        sort_order=0,
        plan_type=plan_type,
        seat_limit=seat_limit,
    )
    db.add(row)
    db.flush()
    return row


def test_institution_owner_is_member(db):
    owner = user(db, 1)
    institution = create_institution(db, owner=owner, name="Archive University", slug="archive-university")

    membership = db.query(InstitutionMembership).filter_by(institution_id=institution.id, user_id=owner.id).one()
    assert membership.role == "owner"
    assert membership.status == "active"


def test_only_institutional_plan_can_be_assigned(db):
    owner = user(db, 1)
    institution = create_institution(db, owner=owner, name="Archive University", slug="archive-university")
    individual = plan(db, code="reader", plan_type="individual")

    with pytest.raises(HTTPException) as exc:
        assign_plan(db, institution=institution, plan_id=individual.id, starts_at=None, ends_at=None)
    assert exc.value.status_code == 422


def test_effective_institutional_plan_is_visible_to_member(db):
    owner = user(db, 1)
    member = user(db, 2)
    institution = create_institution(db, owner=owner, name="Archive University", slug="archive-university")
    add_member(db, institution=institution, user_id=member.id, role="member")
    institutional = plan(db, code="institutional-reader", seat_limit=5)
    assign_plan(db, institution=institution, plan_id=institutional.id, starts_at=None, ends_at=None)

    effective = get_effective_institution_subscription(db, member.id)
    assert effective is not None
    assert effective.plan_id == institutional.id


def test_seat_limit_counts_owner_and_active_members(db):
    owner = user(db, 1)
    member = user(db, 2)
    extra = user(db, 3)
    institution = create_institution(db, owner=owner, name="Archive University", slug="archive-university")
    institutional = plan(db, code="institutional-reader", seat_limit=2)
    assign_plan(db, institution=institution, plan_id=institutional.id, starts_at=None, ends_at=None)

    add_member(db, institution=institution, user_id=member.id, role="member")
    with pytest.raises(HTTPException) as exc:
        add_member(db, institution=institution, user_id=extra.id, role="member")
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "institution_seat_limit_reached"


def test_revoked_members_no_longer_receive_institution_plan(db):
    owner = user(db, 1)
    member = user(db, 2)
    institution = create_institution(db, owner=owner, name="Archive University", slug="archive-university")
    add_member(db, institution=institution, user_id=member.id, role="member")
    institutional = plan(db, code="institutional-reader", seat_limit=5)
    assign_plan(db, institution=institution, plan_id=institutional.id, starts_at=None, ends_at=None)

    revoke_member(db, institution=institution, user_id=member.id)
    assert get_effective_institution_subscription(db, member.id) is None



def test_effective_plan_falls_back_to_institutional_plan(db):
    owner = user(db, 1)
    member = user(db, 2)
    institution = create_institution(db, owner=owner, name="Archive University", slug="archive-university")
    add_member(db, institution=institution, user_id=member.id, role="member")
    institutional = plan(db, code="institutional-reader", seat_limit=5)
    assign_plan(db, institution=institution, plan_id=institutional.id, starts_at=None, ends_at=None)

    effective = get_effective_plan(db, member.id)
    assert effective is not None
    assert effective.id == institutional.id

def test_expired_institution_plan_is_not_effective(db):
    owner = user(db, 1)
    institution = create_institution(db, owner=owner, name="Archive University", slug="archive-university")
    institutional = plan(db, code="institutional-reader", seat_limit=5)
    start = datetime.now(timezone.utc) - timedelta(days=2)
    assign_plan(
        db,
        institution=institution,
        plan_id=institutional.id,
        starts_at=start,
        ends_at=start + timedelta(days=1),
    )
    assert get_effective_institution_subscription(db, owner.id) is None
