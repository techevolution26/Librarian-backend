from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entitlement import Entitlement
from app.models.user import User
from app.schemas.entitlement import BookAccessDecision, EntitlementRead
from app.services.entitlements import resolve_book_access

router = APIRouter(prefix="/entitlements", tags=["entitlements"])


@router.get("/mine", response_model=list[EntitlementRead])
def list_my_entitlements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EntitlementRead]:
    rows = db.scalars(
        select(Entitlement)
        .where(Entitlement.user_id == current_user.id)
        .order_by(Entitlement.created_at.desc(), Entitlement.id.desc())
    ).all()
    return [EntitlementRead.model_validate(row) for row in rows]


@router.get("/books/{book_id}/access", response_model=BookAccessDecision)
def get_book_access(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookAccessDecision:
    allowed, reason, entitlement = resolve_book_access(
        db, user_id=current_user.id, book_id=book_id
    )
    if entitlement is not None:
        db.commit()
    return BookAccessDecision(
        allowed=allowed,
        reason=reason,
        entitlement_id=entitlement.id if entitlement else None,
        source=entitlement.source if entitlement else None,
        expires_at=entitlement.expires_at if entitlement else None,
    )
