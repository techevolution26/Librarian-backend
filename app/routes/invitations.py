from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.circle import Circle
from app.models.circle_member import CircleMember
from app.models.invitation import Invitation, InvitationUse
from app.models.user import User
from app.schemas.invitations import (
    CircleInvitationAcceptRead,
    CircleInvitationCreate,
    CircleInvitationCreateRead,
    CircleInvitationPreviewRead,
    CircleInvitationRead,
    CircleInvitationRevokeRead,
)
from app.services.notifications import create_notification

router = APIRouter(prefix="/invitations", tags=["invitations"])

INVITATION_TYPE_CIRCLE = "CIRCLE"
INVITATION_RATE_LIMIT = 20
INVITATION_URL_PREFIX = "librarian://circle-invite/"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _status(invitation: Invitation, now: datetime) -> str:
    if invitation.status == "revoked":
        return "revoked"
    if invitation.uses >= invitation.max_uses:
        return "consumed"
    if invitation.expires_at <= now:
        return "expired"
    return "active"


def _require_circle_admin(db: Session, circle_id: int, user_id: int) -> tuple[Circle, CircleMember]:
    circle = db.scalar(
        select(Circle).where(Circle.id == circle_id, Circle.archived_at.is_(None)).options(joinedload(Circle.owner))
    )
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")

    member = db.scalar(
        select(CircleMember).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == user_id,
            CircleMember.status == "active",
        )
    )
    if not member or member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return circle, member


@router.post("/circles/{circle_id}", response_model=CircleInvitationCreateRead, status_code=201)
def create_circle_invitation(
    circle_id: int,
    payload: CircleInvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleInvitationCreateRead:
    circle, _ = _require_circle_admin(db, circle_id, current_user.id)
    now = datetime.now(timezone.utc)

    recent_count = db.scalar(
        select(func.count(Invitation.id)).where(
            Invitation.invitation_type == INVITATION_TYPE_CIRCLE,
            Invitation.circle_id == circle_id,
            Invitation.created_by_user_id == current_user.id,
            Invitation.created_at >= now - timedelta(hours=1),
        )
    ) or 0
    if recent_count >= INVITATION_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Invitation creation limit reached. Try again later.")

    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        invitation_type=INVITATION_TYPE_CIRCLE,
        token_hash=_hash_token(token),
        circle_id=circle.id,
        created_by_user_id=current_user.id,
        expires_at=now + timedelta(days=payload.expires_in_days),
        max_uses=payload.max_uses,
        uses=0,
        status="active",
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return CircleInvitationCreateRead(
        id=invitation.id,
        invitation_type=invitation.invitation_type,
        token=token,
        invite_url=f"{INVITATION_URL_PREFIX}{token}",
        expires_at=invitation.expires_at,
        max_uses=invitation.max_uses,
        uses=invitation.uses,
        status="active",
    )


@router.get("/{token}", response_model=CircleInvitationPreviewRead)
def preview_circle_invitation(
    token: str,
    db: Session = Depends(get_db),
) -> CircleInvitationPreviewRead:
    invitation = db.scalar(
        select(Invitation)
        .where(
            Invitation.token_hash == _hash_token(token),
            Invitation.invitation_type == INVITATION_TYPE_CIRCLE,
        )
        .options(joinedload(Invitation.circle), joinedload(Invitation.created_by))
    )
    if not invitation or not invitation.circle or invitation.circle.archived_at is not None:
        raise HTTPException(status_code=404, detail="Invitation not found")

    now = datetime.now(timezone.utc)
    status = _status(invitation, now)
    member_count = db.scalar(
        select(func.count(CircleMember.id)).where(
            CircleMember.circle_id == invitation.circle_id,
            CircleMember.status == "active",
        )
    ) or 0

    return CircleInvitationPreviewRead(
        id=invitation.id,
        invitation_type=invitation.invitation_type,
        circle_id=invitation.circle.id,
        circle_name=invitation.circle.name,
        circle_slug=invitation.circle.slug,
        circle_description=invitation.circle.description,
        circle_visibility=invitation.circle.visibility,
        circle_icon_key=invitation.circle.icon_key,
        member_count=member_count,
        inviter_id=invitation.created_by_user_id,
        inviter_name=invitation.created_by.full_name,
        expires_at=invitation.expires_at,
        max_uses=invitation.max_uses,
        uses=invitation.uses,
        status=status,
        can_accept=status == "active",
    )


@router.post("/{token}/accept", response_model=CircleInvitationAcceptRead)
def accept_circle_invitation(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleInvitationAcceptRead:
    invitation = db.scalar(
        select(Invitation)
        .where(
            Invitation.token_hash == _hash_token(token),
            Invitation.invitation_type == INVITATION_TYPE_CIRCLE,
        )
        .with_for_update()
    )
    if not invitation or not invitation.circle_id:
        raise HTTPException(status_code=404, detail="Invitation not found")

    now = datetime.now(timezone.utc)
    status = _status(invitation, now)
    if status != "active":
        raise HTTPException(status_code=410, detail=f"Invitation is {status}.")

    circle = db.scalar(select(Circle).where(Circle.id == invitation.circle_id, Circle.archived_at.is_(None)))
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")

    existing = db.scalar(
        select(CircleMember).where(
            CircleMember.circle_id == circle.id,
            CircleMember.user_id == current_user.id,
        )
    )
    if existing and existing.status == "active":
        raise HTTPException(status_code=409, detail="You are already a member of this circle.")

    if existing:
        existing.status = "active"
        existing.role = "member"
        existing.invited_by_user_id = invitation.created_by_user_id
        existing.joined_at = now
        member = existing
    else:
        member = CircleMember(
            circle_id=circle.id,
            user_id=current_user.id,
            role="member",
            status="active",
            invited_by_user_id=invitation.created_by_user_id,
            joined_at=now,
        )
        db.add(member)
        db.flush()

    invitation.uses += 1
    invitation.last_used_at = now
    if invitation.uses >= invitation.max_uses:
        invitation.status = "consumed"

    db.add(
        InvitationUse(
            invitation_id=invitation.id,
            user_id=current_user.id,
        )
    )
    create_notification(
        db,
        user_id=invitation.created_by_user_id,
        type="circle.invitation.accepted",
        title="Circle invitation accepted",
        body=f"{current_user.full_name} joined {circle.name} using your invitation.",
        data={"circle_id": circle.id, "invitation_id": invitation.id, "user_id": current_user.id},
    )
    db.commit()
    db.refresh(member)

    return CircleInvitationAcceptRead(
        invitation_id=invitation.id,
        circle_id=circle.id,
        circle_name=circle.name,
        membership_id=member.id,
        status="accepted",
    )


@router.get("/circle/{circle_id}", response_model=list[CircleInvitationRead])
def list_circle_invitations(
    circle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CircleInvitationRead]:
    circle, _ = _require_circle_admin(db, circle_id, current_user.id)
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(Invitation)
        .where(Invitation.circle_id == circle.id, Invitation.invitation_type == INVITATION_TYPE_CIRCLE)
        .order_by(Invitation.created_at.desc())
    ).all()

    return [
        CircleInvitationRead(
            id=row.id,
            invitation_type=row.invitation_type,
            circle_id=circle.id,
            circle_name=circle.name,
            created_by_user_id=row.created_by_user_id,
            expires_at=row.expires_at,
            max_uses=row.max_uses,
            uses=row.uses,
            status=_status(row, now),
            revoked_at=row.revoked_at,
            last_used_at=row.last_used_at,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/{invitation_id}/revoke", response_model=CircleInvitationRevokeRead)
def revoke_circle_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleInvitationRevokeRead:
    invitation = db.scalar(select(Invitation).where(Invitation.id == invitation_id, Invitation.invitation_type == INVITATION_TYPE_CIRCLE))
    if not invitation or not invitation.circle_id:
        raise HTTPException(status_code=404, detail="Invitation not found")

    _require_circle_admin(db, invitation.circle_id, current_user.id)
    if invitation.status == "revoked":
        raise HTTPException(status_code=409, detail="Invitation already revoked.")
    if invitation.uses >= invitation.max_uses:
        raise HTTPException(status_code=409, detail="Consumed invitations cannot be revoked.")

    now = datetime.now(timezone.utc)
    invitation.status = "revoked"
    invitation.revoked_at = now
    invitation.revoked_by_user_id = current_user.id
    db.commit()

    return CircleInvitationRevokeRead(id=invitation.id, status="revoked", revoked_at=now)
