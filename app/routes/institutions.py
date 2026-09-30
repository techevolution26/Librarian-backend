from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.institution import Institution, InstitutionMembership, InstitutionSubscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionMemberCreate,
    InstitutionMembershipRead,
    InstitutionPlanAssign,
    InstitutionRead,
    InstitutionSubscriptionRead,
)
from app.services.institution import add_member, assign_plan, create_institution, get_effective_institution_subscription, require_manager, revoke_member

router = APIRouter(prefix="/institutions", tags=["institutions"])


def _subscription_read(row: InstitutionSubscription) -> InstitutionSubscriptionRead:
    return InstitutionSubscriptionRead(
        id=row.id,
        institution_id=row.institution_id,
        plan_id=row.plan_id,
        plan_code=row.plan.code,
        plan_name=row.plan.name,
        status=row.status,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("", response_model=InstitutionRead, status_code=status.HTTP_201_CREATED)
def create_new_institution(
    payload: InstitutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstitutionRead:
    return InstitutionRead.model_validate(create_institution(db, owner=current_user, name=payload.name, slug=payload.slug))


@router.get("/mine", response_model=list[InstitutionRead])
def list_my_institutions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InstitutionRead]:
    rows = db.scalars(
        select(Institution)
        .join(InstitutionMembership, InstitutionMembership.institution_id == Institution.id)
        .where(InstitutionMembership.user_id == current_user.id, InstitutionMembership.status == "active")
        .order_by(Institution.name.asc(), Institution.id.asc())
    ).all()
    return [InstitutionRead.model_validate(row) for row in rows]


@router.get("/effective-subscription", response_model=InstitutionSubscriptionRead | None)
def get_my_effective_institution_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstitutionSubscriptionRead | None:
    row = get_effective_institution_subscription(db, current_user.id)
    return _subscription_read(row) if row else None


@router.get("/{institution_id}/members", response_model=list[InstitutionMembershipRead])
def list_members(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InstitutionMembershipRead]:
    require_manager(db, institution_id, current_user.id)
    rows = db.scalars(
        select(InstitutionMembership)
        .where(InstitutionMembership.institution_id == institution_id)
        .order_by(InstitutionMembership.created_at.asc(), InstitutionMembership.id.asc())
    ).all()
    return [InstitutionMembershipRead.model_validate(row) for row in rows]


@router.post("/{institution_id}/members", response_model=InstitutionMembershipRead, status_code=status.HTTP_201_CREATED)
def add_institution_member(
    institution_id: int,
    payload: InstitutionMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstitutionMembershipRead:
    require_manager(db, institution_id, current_user.id)
    institution = db.get(Institution, institution_id)
    assert institution is not None
    return InstitutionMembershipRead.model_validate(
        add_member(db, institution=institution, user_id=payload.user_id, role=payload.role)
    )


@router.delete("/{institution_id}/members/{user_id}", response_model=InstitutionMembershipRead)
def revoke_institution_member(
    institution_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstitutionMembershipRead:
    require_manager(db, institution_id, current_user.id)
    institution = db.get(Institution, institution_id)
    assert institution is not None
    return InstitutionMembershipRead.model_validate(revoke_member(db, institution=institution, user_id=user_id))


@router.put("/{institution_id}/plan", response_model=InstitutionSubscriptionRead)
def assign_institution_plan(
    institution_id: int,
    payload: InstitutionPlanAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstitutionSubscriptionRead:
    require_manager(db, institution_id, current_user.id)
    institution = db.get(Institution, institution_id)
    assert institution is not None
    row = assign_plan(
        db,
        institution=institution,
        plan_id=payload.plan_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    return _subscription_read(row)


@router.get("/{institution_id}/plan", response_model=InstitutionSubscriptionRead | None)
def get_institution_plan(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstitutionSubscriptionRead | None:
    require_manager(db, institution_id, current_user.id)
    row = db.scalar(
        select(InstitutionSubscription)
        .where(InstitutionSubscription.institution_id == institution_id, InstitutionSubscription.status == "active")
        .order_by(InstitutionSubscription.starts_at.desc(), InstitutionSubscription.id.desc())
    )
    return _subscription_read(row) if row else None
