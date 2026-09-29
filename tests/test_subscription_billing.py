from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.billing_customer import BillingCustomer
from app.models.billing_webhook_event import BillingWebhookEvent
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.services.subscription_billing import (
    ACTIVE_SUBSCRIPTION_STATUSES,
    get_effective_subscription,
    resolve_plan_for_provider_subscription,
    sync_provider_subscription,
)


def make_db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            SubscriptionPlan.__table__,
            BillingCustomer.__table__,
            Subscription.__table__,
            BillingWebhookEvent.__table__,
        ],
    )
    return Session(engine)


def make_plan(db: Session, *, status: str = "active") -> SubscriptionPlan:
    row = SubscriptionPlan(
        code="reader",
        name="Reader",
        description="Reader plan",
        price_amount_minor=1000,
        currency="usd",
        billing_interval="month",
        status=status,
        stripe_product_id="prod_reader",
        stripe_price_id="price_reader",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def make_user(db: Session) -> User:
    row = User(full_name="Reader", email="reader@example.com", password_hash="x")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def subscription_payload(status: str = "active") -> dict:
    return {
        "id": "sub_123",
        "customer": "cus_123",
        "status": status,
        "metadata": {"plan_id": "1", "librarian_user_id": "1"},
        "items": {"data": [{"quantity": 1, "price": {"id": "price_reader", "product": "prod_reader"}}]},
        "current_period_start": 1_760_000_000,
        "current_period_end": 1_762_600_000,
        "latest_invoice": "in_123",
    }


def test_effective_subscription_statuses_are_explicit():
    assert ACTIVE_SUBSCRIPTION_STATUSES == {"active", "trialing"}


def test_provider_subscription_maps_by_plan_metadata():
    with make_db() as db:
        make_plan(db)
        payload = subscription_payload()
        plan = resolve_plan_for_provider_subscription(db, payload)
        assert plan.code == "reader"


def test_provider_subscription_is_synchronized_idempotently_by_provider_id():
    with make_db() as db:
        plan = make_plan(db)
        user = make_user(db)
        payload = subscription_payload()
        row = sync_provider_subscription(db, payload)
        db.commit()
        assert row.user_id == user.id
        assert row.plan_id == plan.id
        assert row.provider_subscription_id == "sub_123"
        assert row.current_period_start is not None
        assert row.current_period_end is not None

        row2 = sync_provider_subscription(db, payload | {"status": "past_due"})
        db.commit()
        assert row2.id == row.id
        assert row2.status == "past_due"


def test_effective_subscription_requires_active_plan_and_active_status():
    with make_db() as db:
        plan = make_plan(db)
        user = make_user(db)
        customer = BillingCustomer(
            user_id=user.id,
            provider="stripe",
            provider_customer_id="cus_123",
            email=user.email,
        )
        db.add(customer)
        db.flush()
        row = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            billing_customer_id=customer.id,
            provider="stripe",
            provider_subscription_id="sub_123",
            provider_price_id="price_reader",
            status="past_due",
        )
        db.add(row)
        db.commit()
        assert get_effective_subscription(db, user.id) is None

        row.status = "active"
        db.commit()
        effective = get_effective_subscription(db, user.id)
        assert effective is not None
        assert effective.plan.code == "reader"
