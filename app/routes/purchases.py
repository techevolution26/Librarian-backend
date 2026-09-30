from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.purchase import Purchase
from app.models.user import User
from app.schemas.purchase import PurchaseCheckoutCreate, PurchaseCheckoutRead, PurchaseRead
from app.services.purchases import create_purchase_checkout, get_purchase_for_user

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.get("/mine", response_model=list[PurchaseRead])
def list_my_purchases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PurchaseRead]:
    rows = db.scalars(
        select(Purchase)
        .where(Purchase.user_id == current_user.id)
        .order_by(Purchase.created_at.desc(), Purchase.id.desc())
    ).all()
    return [PurchaseRead.model_validate(row) for row in rows]


@router.get("/{purchase_id}", response_model=PurchaseRead)
def get_my_purchase(
    purchase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PurchaseRead:
    return PurchaseRead.model_validate(get_purchase_for_user(db, current_user.id, purchase_id))


@router.post("/books/{paid_offer_id}/checkout", response_model=PurchaseCheckoutRead)
def checkout_paid_book(
    paid_offer_id: int,
    payload: PurchaseCheckoutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PurchaseCheckoutRead:
    purchase, session_id, checkout_url = create_purchase_checkout(
        db,
        current_user,
        paid_offer_id=paid_offer_id,
        idempotency_key=payload.idempotency_key,
    )
    return PurchaseCheckoutRead(
        purchase_id=purchase.id,
        checkout_session_id=session_id,
        checkout_url=checkout_url,
    )
