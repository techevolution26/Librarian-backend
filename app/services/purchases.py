from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.creator_hosted_book import CreatorHostedBook
from app.models.creator_paid_book import CreatorPaidBook
from app.models.entitlement import Entitlement
from app.models.purchase import Purchase
from app.models.user import User
from app.services.creator_lifetime_access import (
    grant_lifetime_access_from_purchase,
    revoke_lifetime_access_for_purchase,
)


def _stripe() -> Any:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Purchase billing is not configured")
    try:
        import stripe
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Stripe billing dependency is unavailable") from exc
    stripe.api_key = settings.stripe_secret_key
    return stripe


def _checkout_urls() -> tuple[str, str]:
    settings = get_settings()
    if not settings.stripe_success_url or not settings.stripe_cancel_url:
        raise HTTPException(status_code=503, detail="Stripe checkout URLs are not configured")
    return settings.stripe_success_url, settings.stripe_cancel_url


def _get_offer_for_purchase(db: Session, paid_offer_id: int) -> tuple[CreatorPaidBook, CreatorHostedBook]:
    offer = db.get(CreatorPaidBook, paid_offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Paid offer not found")
    if offer.status != "active":
        raise HTTPException(status_code=409, detail="This paid offer is not available for purchase")
    hosted = db.get(CreatorHostedBook, offer.hosted_book_id)
    if hosted is None or hosted.status != "hosted":
        raise HTTPException(status_code=409, detail="This book is not currently available for purchase")
    return offer, hosted


def get_purchase_for_user(db: Session, user_id: int, purchase_id: int) -> Purchase:
    purchase = db.scalar(
        select(Purchase).where(Purchase.id == purchase_id, Purchase.user_id == user_id)
    )
    if purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase


def create_purchase_checkout(
    db: Session,
    user: User,
    paid_offer_id: int,
    idempotency_key: str,
) -> tuple[Purchase, str, str]:
    existing = db.scalar(
        select(Purchase).where(
            Purchase.user_id == user.id,
            Purchase.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.provider_checkout_session_id:
            stripe = _stripe()
            session = stripe.checkout.Session.retrieve(existing.provider_checkout_session_id)
            if not session.url:
                raise HTTPException(status_code=502, detail="Stripe checkout session has no URL")
            return existing, str(session.id), str(session.url)
        raise HTTPException(status_code=409, detail="Purchase exists but has no checkout session")

    offer, hosted = _get_offer_for_purchase(db, paid_offer_id)

    purchase = Purchase(
        user_id=user.id,
        paid_offer_id=offer.id,
        hosted_book_id=hosted.id,
        amount_minor=offer.price_amount_minor,
        currency=offer.currency.lower(),
        provider="stripe",
        status="pending",
        idempotency_key=idempotency_key,
    )
    db.add(purchase)
    db.flush()

    success_url, cancel_url = _checkout_urls()
    stripe = _stripe()
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            customer_email=user.email,
            line_items=[
                {
                    "price_data": {
                        "currency": offer.currency.lower(),
                        "unit_amount": offer.price_amount_minor,
                        "product_data": {
                            "name": hosted.book.title,
                            "metadata": {
                                "librarian_paid_offer_id": str(offer.id),
                                "librarian_hosted_book_id": str(hosted.id),
                            },
                        },
                    },
                    "quantity": 1,
                }
            ],
            client_reference_id=str(user.id),
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "librarian_purchase_id": str(purchase.id),
                "librarian_user_id": str(user.id),
                "librarian_paid_offer_id": str(offer.id),
                "librarian_hosted_book_id": str(hosted.id),
            },
            payment_intent_data={
                "metadata": {
                    "librarian_purchase_id": str(purchase.id),
                    "librarian_user_id": str(user.id),
                    "librarian_paid_offer_id": str(offer.id),
                }
            },
            idempotency_key=f"librarian-purchase-{purchase.id}-{idempotency_key}",
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail="Stripe checkout session could not be created") from exc

    if not session.url:
        db.rollback()
        raise HTTPException(status_code=502, detail="Stripe did not return a checkout URL")

    purchase.provider_checkout_session_id = str(session.id)
    purchase.provider_customer_id = str(session.customer) if session.customer else None
    db.commit()
    db.refresh(purchase)
    return purchase, str(session.id), str(session.url)


def _purchase_from_checkout(db: Session, data: dict[str, Any]) -> Purchase | None:
    metadata = data.get("metadata") or {}
    purchase_id = metadata.get("librarian_purchase_id")
    if purchase_id:
        purchase = db.get(Purchase, int(purchase_id))
        if purchase:
            return purchase
    session_id = data.get("id")
    if session_id:
        return db.scalar(
            select(Purchase).where(
                Purchase.provider == "stripe",
                Purchase.provider_checkout_session_id == str(session_id),
            )
        )
    return None


def mark_purchase_paid(db: Session, purchase: Purchase, data: dict[str, Any]) -> Purchase:
    if purchase.status == "refunded":
        return purchase
    if purchase.status == "paid":
        return purchase

    payment_intent = data.get("payment_intent")
    if payment_intent:
        purchase.provider_payment_intent_id = str(payment_intent)
    if data.get("customer"):
        purchase.provider_customer_id = str(data["customer"])

    purchase.status = "paid"
    purchase.purchased_at = purchase.purchased_at or datetime.now(timezone.utc)
    grant_lifetime_access_from_purchase(db, purchase)
    db.flush()
    return purchase


def mark_purchase_failed(db: Session, purchase: Purchase) -> Purchase:
    if purchase.status not in {"paid", "refunded"}:
        purchase.status = "failed"
    return purchase


def mark_purchase_cancelled(db: Session, purchase: Purchase) -> Purchase:
    if purchase.status == "pending":
        purchase.status = "cancelled"
    return purchase


def mark_purchase_refunded(db: Session, purchase: Purchase) -> Purchase:
    if purchase.status == "refunded":
        return purchase
    purchase.status = "refunded"
    purchase.refunded_at = purchase.refunded_at or datetime.now(timezone.utc)
    revoke_lifetime_access_for_purchase(db, purchase)
    db.flush()
    return purchase


def process_verified_stripe_purchase_event(db: Session, event_type: str, data: dict[str, Any]) -> Purchase | None:
    """Apply a signature-verified Stripe purchase event.

    This function assumes webhook signature verification and event-level
    idempotency are handled by the caller. Verified payment creates durable
    lifetime ownership; it never creates creator revenue ledger entries.
    """
    if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        if str(data.get("mode") or "") != "payment":
            return None
        purchase = _purchase_from_checkout(db, data)
        if purchase is None:
            raise ValueError("Stripe checkout session is not linked to a Librarian purchase")
        payment_status = str(data.get("payment_status") or "")
        if event_type == "checkout.session.completed" and payment_status != "paid":
            return purchase
        return mark_purchase_paid(db, purchase, data)

    if event_type == "checkout.session.async_payment_failed":
        if str(data.get("mode") or "") != "payment":
            return None
        purchase = _purchase_from_checkout(db, data)
        if purchase is None:
            raise ValueError("Stripe checkout session is not linked to a Librarian purchase")
        return mark_purchase_failed(db, purchase)

    if event_type == "checkout.session.expired":
        if str(data.get("mode") or "") != "payment":
            return None
        purchase = _purchase_from_checkout(db, data)
        if purchase is None:
            return None
        return mark_purchase_cancelled(db, purchase)

    if event_type == "charge.refunded":
        payment_intent = data.get("payment_intent")
        if not payment_intent:
            return None
        purchase = db.scalar(
            select(Purchase).where(
                Purchase.provider == "stripe",
                Purchase.provider_payment_intent_id == str(payment_intent),
            )
        )
        if purchase is None:
            return None
        return mark_purchase_refunded(db, purchase)

    return None
