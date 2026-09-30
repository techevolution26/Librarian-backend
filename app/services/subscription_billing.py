from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.billing_customer import BillingCustomer
from app.models.billing_webhook_event import BillingWebhookEvent
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.services.purchases import process_verified_stripe_purchase_event
from app.services.institution import get_effective_institution_subscription


ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


def _stripe() -> Any:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Subscription billing is not configured")
    try:
        import stripe
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Stripe billing dependency is unavailable") from exc
    stripe.api_key = settings.stripe_secret_key
    return stripe


def _unix_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


def ensure_stripe_customer(db: Session, user: User) -> BillingCustomer:
    existing = db.scalar(
        select(BillingCustomer).where(
            BillingCustomer.user_id == user.id,
            BillingCustomer.provider == "stripe",
        )
    )
    if existing:
        return existing

    stripe = _stripe()
    customer = stripe.Customer.create(
        email=user.email,
        name=user.full_name,
        metadata={"librarian_user_id": str(user.id)},
        idempotency_key=f"librarian-customer-{user.id}",
    )
    row = BillingCustomer(
        user_id=user.id,
        provider="stripe",
        provider_customer_id=str(customer.id),
        email=user.email,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        row = db.scalar(
            select(BillingCustomer).where(
                BillingCustomer.user_id == user.id,
                BillingCustomer.provider == "stripe",
            )
        )
        if not row:
            raise
    return row


def get_current_subscription(db: Session, user_id: int) -> Subscription | None:
    return db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc(), Subscription.id.desc())
    )


def get_effective_subscription(db: Session, user_id: int) -> Subscription | None:
    return db.scalar(
        select(Subscription)
        .join(SubscriptionPlan, SubscriptionPlan.id == Subscription.plan_id)
        .where(
            Subscription.user_id == user_id,
            Subscription.status.in_(ACTIVE_SUBSCRIPTION_STATUSES),
            SubscriptionPlan.status == "active",
        )
        .order_by(Subscription.created_at.desc(), Subscription.id.desc())
    )


def get_effective_plan(db: Session, user_id: int) -> SubscriptionPlan | None:
    """Resolve direct subscription first, then an active institutional plan."""
    direct = get_effective_subscription(db, user_id)
    if direct is not None:
        return direct.plan
    institutional = get_effective_institution_subscription(db, user_id)
    return institutional.plan if institutional is not None else None


def create_checkout_session(db: Session, user: User, plan_code: str, idempotency_key: str) -> dict[str, str]:
    plan = db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.code == plan_code.strip().lower(),
            SubscriptionPlan.status == "active",
        )
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")
    if plan.price_amount_minor <= 0 or plan.billing_interval not in {"month", "year"}:
        raise HTTPException(status_code=422, detail="Selected plan is not a paid recurring plan")
    if not plan.stripe_price_id:
        raise HTTPException(status_code=409, detail="Selected plan is not connected to a Stripe price")
    if get_effective_subscription(db, user.id):
        raise HTTPException(status_code=409, detail="An active subscription already exists")

    customer = ensure_stripe_customer(db, user)
    settings = get_settings()
    if not settings.stripe_success_url or not settings.stripe_cancel_url:
        raise HTTPException(status_code=503, detail="Stripe checkout URLs are not configured")

    stripe = _stripe()
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer.provider_customer_id,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        client_reference_id=str(user.id),
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        metadata={"librarian_user_id": str(user.id), "plan_id": str(plan.id), "plan_code": plan.code},
        subscription_data={
            "metadata": {"librarian_user_id": str(user.id), "plan_id": str(plan.id), "plan_code": plan.code}
        },
        idempotency_key=idempotency_key,
    )
    if not session.url:
        raise HTTPException(status_code=502, detail="Stripe did not return a checkout URL")
    return {"checkout_session_id": str(session.id), "checkout_url": str(session.url)}


def create_customer_portal_session(db: Session, user: User) -> str:
    customer = db.scalar(
        select(BillingCustomer).where(
            BillingCustomer.user_id == user.id,
            BillingCustomer.provider == "stripe",
        )
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Billing customer not found")
    settings = get_settings()
    if not settings.stripe_portal_return_url:
        raise HTTPException(status_code=503, detail="Stripe portal return URL is not configured")
    stripe = _stripe()
    session = stripe.billing_portal.Session.create(
        customer=customer.provider_customer_id,
        return_url=settings.stripe_portal_return_url,
    )
    return str(session.url)


def resolve_plan_for_provider_subscription(
    db: Session, subscription_data: dict[str, Any]
) -> SubscriptionPlan:
    metadata = subscription_data.get("metadata") or {}
    plan_id = metadata.get("plan_id")
    if plan_id:
        plan = db.get(SubscriptionPlan, int(plan_id))
        if plan:
            return plan

    items = subscription_data.get("items") or {}
    data = items.get("data") or []
    price_id = None
    if data:
        price = data[0].get("price") or {}
        price_id = price.get("id")
    if price_id:
        plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.stripe_price_id == price_id))
        if plan:
            return plan
    raise ValueError("Unable to map Stripe subscription to a Librarian plan")


def sync_provider_subscription(db: Session, data: dict[str, Any]) -> Subscription:
    provider_subscription_id = str(data["id"])
    provider_customer_id = str(data["customer"])
    metadata = data.get("metadata") or {}
    plan = resolve_plan_for_provider_subscription(db, data)

    customer = db.scalar(
        select(BillingCustomer).where(
            BillingCustomer.provider == "stripe",
            BillingCustomer.provider_customer_id == provider_customer_id,
        )
    )
    if not customer:
        user_id = metadata.get("librarian_user_id")
        if not user_id:
            raise ValueError("Stripe customer is not linked to a Librarian user")
        user = db.get(User, int(user_id))
        if not user:
            raise ValueError("Stripe customer references an unknown Librarian user")
        customer = BillingCustomer(
            user_id=user.id,
            provider="stripe",
            provider_customer_id=provider_customer_id,
            email=user.email,
        )
        db.add(customer)
        db.flush()

    row = db.scalar(
        select(Subscription).where(
            Subscription.provider == "stripe",
            Subscription.provider_subscription_id == provider_subscription_id,
        )
    )
    if not row:
        row = Subscription(
            user_id=customer.user_id,
            plan_id=plan.id,
            billing_customer_id=customer.id,
            provider="stripe",
            provider_subscription_id=provider_subscription_id,
            provider_price_id="",
            status="incomplete",
        )
        db.add(row)

    items = data.get("items") or {}
    item_data = items.get("data") or []
    item = item_data[0] if item_data else {}
    price = item.get("price") or {}
    row.plan_id = plan.id
    row.billing_customer_id = customer.id
    row.user_id = customer.user_id
    row.provider_price_id = str(price.get("id") or row.provider_price_id)
    product = price.get("product")
    row.provider_product_id = str(product) if product else row.provider_product_id
    row.status = str(data.get("status") or "incomplete")
    row.quantity = int(item.get("quantity") or 1)
    row.current_period_start = _unix_datetime(data.get("current_period_start"))
    row.current_period_end = _unix_datetime(data.get("current_period_end"))
    row.trial_start = _unix_datetime(data.get("trial_start"))
    row.trial_end = _unix_datetime(data.get("trial_end"))
    row.cancel_at = _unix_datetime(data.get("cancel_at"))
    row.canceled_at = _unix_datetime(data.get("canceled_at"))
    row.ended_at = _unix_datetime(data.get("ended_at"))
    row.latest_invoice_id = str(data.get("latest_invoice")) if data.get("latest_invoice") else row.latest_invoice_id
    return row


def process_stripe_webhook(db: Session, payload: bytes, signature: str) -> str:
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook secret is not configured")
    try:
        import stripe
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Stripe billing dependency is unavailable") from exc

    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature") from exc

    event_id = str(event["id"])
    event_type = str(event["type"])
    existing = db.scalar(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.provider == "stripe",
            BillingWebhookEvent.provider_event_id == event_id,
        )
    )
    if existing:
        return "already_processed"

    data = event["data"]["object"]
    try:
        if event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
            sync_provider_subscription(db, data)
        elif event_type == "checkout.session.completed":
            purchase = process_verified_stripe_purchase_event(db, event_type, data)
            if purchase is None:
                subscription_id = data.get("subscription")
                if subscription_id:
                    row = db.scalar(
                        select(Subscription).where(
                            Subscription.provider == "stripe",
                            Subscription.provider_subscription_id == str(subscription_id),
                        )
                    )
                    if row:
                        row.checkout_session_id = str(data["id"])
        elif event_type in {"checkout.session.async_payment_succeeded", "checkout.session.async_payment_failed", "checkout.session.expired", "charge.refunded"}:
            process_verified_stripe_purchase_event(db, event_type, data)
        elif event_type == "invoice.paid":
            subscription_id = data.get("subscription")
            if subscription_id:
                row = db.scalar(
                    select(Subscription).where(
                        Subscription.provider == "stripe",
                        Subscription.provider_subscription_id == str(subscription_id),
                    )
                )
                if row:
                    row.latest_invoice_id = str(data["id"])

        receipt = BillingWebhookEvent(
            provider="stripe",
            provider_event_id=event_id,
            event_type=event_type,
            payload_hash=sha256(payload).hexdigest(),
        )
        db.add(receipt)
        db.commit()
        return "processed"
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(BillingWebhookEvent).where(
                BillingWebhookEvent.provider == "stripe",
                BillingWebhookEvent.provider_event_id == event_id,
            )
        )
        if existing:
            return "already_processed"
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="Stripe event could not be synchronized") from exc
