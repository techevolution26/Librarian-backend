from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.institution import (
    INSTITUTION_MEMBER_ROLES,
    INSTITUTION_MEMBERSHIP_STATUSES,
    INSTITUTION_STATUSES,
    INSTITUTION_SUBSCRIPTION_STATUSES,
    Institution,
    InstitutionMembership,
    InstitutionSubscription,
)
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_membership(db: Session, institution_id: int, user_id: int) -> InstitutionMembership | None:
    return db.scalar(
        select(InstitutionMembership).where(
            InstitutionMembership.institution_id == institution_id,
            InstitutionMembership.user_id == user_id,
            InstitutionMembership.status == "active",
        )
    )


def require_manager(db: Session, institution_id: int, user_id: int) -> InstitutionMembership:
    institution = db.get(Institution, institution_id)
    if institution is None or institution.status != "active":
        raise HTTPException(status_code=404, detail="Institution not found")
    membership = get_membership(db, institution_id, user_id)
    if membership is None or membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Institution administrator access required")
    return membership


def create_institution(db: Session, *, owner: User, name: str, slug: str) -> Institution:
    if db.scalar(select(Institution).where(Institution.slug == slug)) is not None:
        raise HTTPException(status_code=409, detail="Institution slug already exists")
    row = Institution(name=name, slug=slug, owner_user_id=owner.id, status="active")
    db.add(row)
    db.flush()
    db.add(InstitutionMembership(institution_id=row.id, user_id=owner.id, role="owner", status="active"))
    db.commit()
    db.refresh(row)
    return row


def get_active_plan_for_institution(db: Session, institution_id: int) -> SubscriptionPlan | None:
    now = _now()
    return db.scalar(
        select(SubscriptionPlan)
        .join(InstitutionSubscription, InstitutionSubscription.plan_id == SubscriptionPlan.id)
        .where(
            InstitutionSubscription.institution_id == institution_id,
            InstitutionSubscription.status == "active",
            InstitutionSubscription.starts_at <= now,
            (InstitutionSubscription.ends_at.is_(None) | (InstitutionSubscription.ends_at > now)),
            SubscriptionPlan.status == "active",
            SubscriptionPlan.plan_type == "institutional",
        )
        .order_by(InstitutionSubscription.starts_at.desc(), InstitutionSubscription.id.desc())
    )


def add_member(db: Session, *, institution: Institution, user_id: int, role: str) -> InstitutionMembership:
    if institution.status != "active":
        raise HTTPException(status_code=409, detail="Institution is not active")
    if role not in {"admin", "member"}:
        raise HTTPException(status_code=422, detail="Invalid institution member role")
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    plan = get_active_plan_for_institution(db, institution.id)
    if plan is not None and plan.seat_limit is not None:
        active_count = len(db.scalars(
            select(InstitutionMembership.id).where(
                InstitutionMembership.institution_id == institution.id,
                InstitutionMembership.status == "active",
            )
        ).all())
        existing_member = db.scalar(
            select(InstitutionMembership.id).where(
                InstitutionMembership.institution_id == institution.id,
                InstitutionMembership.user_id == user_id,
                InstitutionMembership.status == "active",
            )
        )
        if existing_member is None and active_count >= plan.seat_limit:
            raise HTTPException(status_code=403, detail={
                "code": "institution_seat_limit_reached",
                "message": "Institution seat limit reached",
                "count": active_count,
                "limit": plan.seat_limit,
            })
    existing = db.scalar(
        select(InstitutionMembership).where(
            InstitutionMembership.institution_id == institution.id,
            InstitutionMembership.user_id == user_id,
        )
    )
    if existing:
        if existing.status == "active":
            raise HTTPException(status_code=409, detail="User is already an institution member")
        existing.status = "active"
        existing.role = role
        db.commit()
        db.refresh(existing)
        return existing
    row = InstitutionMembership(institution_id=institution.id, user_id=user_id, role=role, status="active")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def revoke_member(db: Session, *, institution: Institution, user_id: int) -> InstitutionMembership:
    row = db.scalar(
        select(InstitutionMembership).where(
            InstitutionMembership.institution_id == institution.id,
            InstitutionMembership.user_id == user_id,
            InstitutionMembership.status == "active",
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Active institution membership not found")
    if row.role == "owner":
        raise HTTPException(status_code=409, detail="The institution owner cannot be revoked")
    row.status = "revoked"
    db.commit()
    db.refresh(row)
    return row


def assign_plan(
    db: Session,
    *,
    institution: Institution,
    plan_id: int,
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> InstitutionSubscription:
    plan = db.get(SubscriptionPlan, plan_id)
    if plan is None or plan.status != "active":
        raise HTTPException(status_code=404, detail="Active subscription plan not found")
    if plan.plan_type != "institutional":
        raise HTTPException(status_code=422, detail="Selected plan is not an institutional plan")
    start = starts_at or _now()
    if ends_at is not None and ends_at <= start:
        raise HTTPException(status_code=422, detail="Institutional plan end must be after its start")

    db.query(InstitutionSubscription).filter(
        InstitutionSubscription.institution_id == institution.id,
        InstitutionSubscription.status == "active",
    ).update({"status": "canceled", "ends_at": start}, synchronize_session=False)

    row = InstitutionSubscription(
        institution_id=institution.id,
        plan_id=plan.id,
        status="active",
        starts_at=start,
        ends_at=ends_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_effective_institution_subscription(db: Session, user_id: int) -> InstitutionSubscription | None:
    now = _now()
    return db.scalar(
        select(InstitutionSubscription)
        .join(Institution, Institution.id == InstitutionSubscription.institution_id)
        .join(InstitutionMembership, InstitutionMembership.institution_id == Institution.id)
        .join(SubscriptionPlan, SubscriptionPlan.id == InstitutionSubscription.plan_id)
        .where(
            InstitutionMembership.user_id == user_id,
            InstitutionMembership.status == "active",
            Institution.status == "active",
            InstitutionSubscription.status == "active",
            InstitutionSubscription.starts_at <= now,
            (InstitutionSubscription.ends_at.is_(None) | (InstitutionSubscription.ends_at > now)),
            SubscriptionPlan.status == "active",
        )
        .order_by(InstitutionSubscription.starts_at.desc(), InstitutionSubscription.id.desc())
    )
