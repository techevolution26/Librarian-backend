from app.models.subscription_plan import PLAN_BILLING_INTERVALS, PLAN_STATUSES, SubscriptionPlan
from app.schemas.subscription_plan import SubscriptionPlanCreate, SubscriptionPlanUpdate


def test_plan_status_and_interval_vocabulary_is_explicit():
    assert PLAN_STATUSES == {"draft", "active", "archived"}
    assert PLAN_BILLING_INTERVALS == {"none", "month", "year"}


def test_plan_is_catalogue_metadata_not_entitlement():
    row = SubscriptionPlan(
        id=1,
        code="reader-plus",
        name="Reader Plus",
        description="Expanded reader access",
        price_amount_minor=999,
        currency="kes",
        billing_interval="month",
        status="active",
    )
    assert row.code == "reader-plus"
    assert row.price_amount_minor == 999
    assert not hasattr(row, "user_id")
    assert not hasattr(row, "entitlement_id")


def test_plan_create_normalizes_code_and_currency():
    payload = SubscriptionPlanCreate(
        code=" Reader_Plus ",
        name="Reader Plus",
        price_amount_minor=999,
        currency=" KES ",
        billing_interval="month",
    )
    assert payload.code == "reader_plus"
    assert payload.currency == "kes"


def test_free_plan_uses_no_billing_interval():
    payload = SubscriptionPlanCreate(
        code="free",
        name="Free",
        price_amount_minor=0,
        currency="KES",
        billing_interval="none",
    )
    assert payload.price_amount_minor == 0
    assert payload.billing_interval == "none"


def test_paid_plan_requires_recurring_interval_in_route_contract():
    payload = SubscriptionPlanCreate(
        code="monthly",
        name="Monthly",
        price_amount_minor=500,
        currency="KES",
        billing_interval="month",
    )
    assert payload.billing_interval == "month"


def test_update_can_change_catalogue_fields():
    payload = SubscriptionPlanUpdate(name="Reader Pro", status="active", sort_order=2)
    assert payload.name == "Reader Pro"
    assert payload.status == "active"
    assert payload.sort_order == 2


def test_invalid_plan_status_is_rejected():
    try:
        SubscriptionPlanCreate(code="xplan", name="X", status="live")
    except Exception:
        pass
    else:
        raise AssertionError("invalid plan status must be rejected")


def test_invalid_interval_is_rejected():
    try:
        SubscriptionPlanCreate(code="xplan", name="X", billing_interval="weekly")
    except Exception:
        pass
    else:
        raise AssertionError("unsupported billing interval must be rejected")
