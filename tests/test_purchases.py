from types import SimpleNamespace
from unittest.mock import patch

from app.models.purchase import PURCHASE_PROVIDERS, PURCHASE_STATUSES, Purchase
from app.schemas.purchase import PurchaseCheckoutCreate
from app.services.purchases import mark_purchase_paid, mark_purchase_refunded, process_verified_stripe_purchase_event


def test_purchase_status_and_provider_vocabulary_is_explicit():
    assert PURCHASE_STATUSES == {"pending", "paid", "failed", "cancelled", "refunded"}
    assert PURCHASE_PROVIDERS == {"stripe"}


def test_purchase_is_transaction_state_not_entitlement_or_revenue():
    row = Purchase(
        user_id=1,
        paid_offer_id=2,
        hosted_book_id=3,
        amount_minor=1500,
        currency="kes",
        provider="stripe",
        status="pending",
        idempotency_key="purchase-test-001",
    )
    assert row.status == "pending"
    assert not hasattr(row, "entitlement_id")
    assert not hasattr(row, "creator_share_minor")


def test_checkout_request_requires_a_stable_idempotency_key():
    payload = PurchaseCheckoutCreate(idempotency_key="  client-purchase-001  ")
    assert payload.idempotency_key == "client-purchase-001"


def test_paid_purchase_materializes_lifetime_ownership_without_creator_revenue():
    purchase = SimpleNamespace(
        id=44,
        user_id=7,
        status="pending",
        purchased_at=None,
        provider_payment_intent_id=None,
        provider_customer_id=None,
        hosted_book=SimpleNamespace(book_id=99),
    )
    db = SimpleNamespace(flush=lambda: None)
    with patch("app.services.purchases.grant_lifetime_access_from_purchase") as grant:
        result = mark_purchase_paid(
            db,
            purchase,
            {"payment_intent": "pi_123", "customer": "cus_123"},
        )
    assert result.status == "paid"
    assert result.provider_payment_intent_id == "pi_123"
    grant.assert_called_once()
    grant.assert_called_once_with(db, purchase)


def test_verified_purchase_event_ignores_subscription_checkout_sessions():
    db = SimpleNamespace()
    result = process_verified_stripe_purchase_event(
        db,
        "checkout.session.completed",
        {"id": "cs_sub", "mode": "subscription", "subscription": "sub_1"},
    )
    assert result is None


def test_refund_revokes_lifetime_ownership_created_by_purchase():
    purchase = SimpleNamespace(
        id=44,
        user_id=7,
        status="paid",
        refunded_at=None,
        hosted_book=SimpleNamespace(book_id=99),
    )
    db = SimpleNamespace(flush=lambda: None)
    with patch("app.services.purchases.revoke_lifetime_access_for_purchase") as revoke:
        result = mark_purchase_refunded(db, purchase)
    assert result.status == "refunded"
    revoke.assert_called_once_with(db, purchase)
