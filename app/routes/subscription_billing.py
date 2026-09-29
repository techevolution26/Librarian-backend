from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.billing import BillingStatusRead
from app.schemas.subscription import (
    CheckoutSessionCreate,
    CheckoutSessionRead,
    CustomerPortalRead,
    SubscriptionRead,
)
from app.services.subscription_billing import (
    create_checkout_session,
    create_customer_portal_session,
    get_effective_subscription,
    get_current_subscription,
    process_stripe_webhook,
)
from app.core.config import get_settings
from app.models.billing_customer import BillingCustomer

router = APIRouter(prefix="/billing", tags=["subscription-billing"])


def _read(row) -> SubscriptionRead:
    return SubscriptionRead(
        id=row.id,
        plan_id=row.plan_id,
        plan_code=row.plan.code,
        plan_name=row.plan.name,
        provider=row.provider,
        provider_subscription_id=row.provider_subscription_id,
        status=row.status,
        quantity=row.quantity,
        current_period_start=row.current_period_start,
        current_period_end=row.current_period_end,
        trial_start=row.trial_start,
        trial_end=row.trial_end,
        cancel_at=row.cancel_at,
        canceled_at=row.canceled_at,
        ended_at=row.ended_at,
    )


@router.get("/subscription", response_model=SubscriptionRead | None)
def get_my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionRead | None:
    row = get_current_subscription(db, current_user.id)
    return _read(row) if row else None


@router.get("/status", response_model=BillingStatusRead)
def get_billing_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BillingStatusRead:
    settings = get_settings()
    customer = db.query(BillingCustomer).filter(
        BillingCustomer.user_id == current_user.id,
        BillingCustomer.provider == "stripe",
    ).first()
    effective = get_effective_subscription(db, current_user.id)
    return BillingStatusRead(
        provider="stripe",
        configured=bool(settings.stripe_secret_key),
        has_customer=customer is not None,
        has_subscription=get_current_subscription(db, current_user.id) is not None,
        effective_plan_code=effective.plan.code if effective else None,
    )


@router.post("/checkout", response_model=CheckoutSessionRead)
def start_checkout(
    payload: CheckoutSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckoutSessionRead:
    result = create_checkout_session(
        db,
        current_user,
        plan_code=payload.plan_code,
        idempotency_key=payload.idempotency_key,
    )
    db.commit()
    return CheckoutSessionRead(**result)


@router.post("/portal", response_model=CustomerPortalRead)
def create_portal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomerPortalRead:
    return CustomerPortalRead(portal_url=create_customer_portal_session(db, current_user))


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    payload = await request.body()
    result = process_stripe_webhook(db, payload, stripe_signature)
    return {"status": result}
