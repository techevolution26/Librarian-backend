from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.circle import Circle
from app.models.circle_annotation import CircleAnnotation
from app.models.circle_discussion import CircleDiscussion, CircleDiscussionReply
from app.models.circle_member import CircleMember
from app.models.circle_moderation import CircleModerationReport
from app.models.user import User
from app.schemas.circle_moderation import (
    CircleModerationReportCreate,
    CircleModerationReportRead,
    CircleModerationReview,
)

router = APIRouter(prefix="/circles/{circle_id}/moderation", tags=["circle moderation"])

TARGET_MODELS = {
    "annotation": CircleAnnotation,
    "discussion": CircleDiscussion,
    "reply": CircleDiscussionReply,
}


def require_member(db: Session, circle_id: int, user_id: int) -> CircleMember:
    member = db.scalar(select(CircleMember).where(
        CircleMember.circle_id == circle_id,
        CircleMember.user_id == user_id,
        CircleMember.status == "active",
    ))
    if not member:
        raise HTTPException(status_code=403, detail="Not a circle member")
    return member


def require_moderator(db: Session, circle_id: int, user_id: int) -> CircleMember:
    member = require_member(db, circle_id, user_id)
    if member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Circle moderation access required")
    return member


def get_target(db: Session, circle_id: int, target_type: str, target_id: int):
    model = TARGET_MODELS.get(target_type)
    if model is None:
        raise HTTPException(status_code=422, detail="Unsupported moderation target")
    row = db.scalar(select(model).where(model.id == target_id))
    if not row:
        raise HTTPException(status_code=404, detail="Moderation target not found")
    if row.circle_id != circle_id:
        raise HTTPException(status_code=404, detail="Moderation target not found")
    if getattr(row, "deleted_at", None) is not None:
        raise HTTPException(status_code=404, detail="Moderation target not found")
    return row


def read_report(db: Session, row: CircleModerationReport) -> CircleModerationReportRead:
    target = get_target(db, row.circle_id, row.target_type, row.target_id)
    author = db.scalar(select(User).where(User.id == target.user_id))
    preview = getattr(target, "body", "").strip().replace("\n", " ")[:500]
    return CircleModerationReportRead(
        id=row.id,
        circle_id=row.circle_id,
        reporter_user_id=row.reporter_user_id,
        target_type=row.target_type,
        target_id=row.target_id,
        reason=row.reason,
        details=row.details,
        status=row.status,
        reviewed_by_user_id=row.reviewed_by_user_id,
        reviewed_at=row.reviewed_at,
        action=row.action,
        action_note=row.action_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
        reporter_name=row.reporter.full_name,
        reviewer_name=row.reviewer.full_name if row.reviewer else None,
        target_preview=preview,
        target_author_name=author.full_name if author else "Unknown author",
    )


@router.post("/reports", response_model=CircleModerationReportRead, status_code=status.HTTP_201_CREATED)
def report_content(
    circle_id: int,
    payload: CircleModerationReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleModerationReportRead:
    require_member(db, circle_id, current_user.id)
    get_target(db, circle_id, payload.target_type, payload.target_id)

    existing = db.scalar(select(CircleModerationReport).where(
        CircleModerationReport.circle_id == circle_id,
        CircleModerationReport.reporter_user_id == current_user.id,
        CircleModerationReport.target_type == payload.target_type,
        CircleModerationReport.target_id == payload.target_id,
        CircleModerationReport.status == "open",
    ))
    if existing:
        raise HTTPException(status_code=409, detail="You already reported this content")

    row = CircleModerationReport(
        circle_id=circle_id,
        reporter_user_id=current_user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        details=payload.details,
        status="open",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row = db.scalar(select(CircleModerationReport).where(CircleModerationReport.id == row.id).options(
        joinedload(CircleModerationReport.reporter), joinedload(CircleModerationReport.reviewer)
    ))
    return read_report(db, row)


@router.get("/reports", response_model=list[CircleModerationReportRead])
def list_reports(
    circle_id: int,
    include_resolved: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CircleModerationReportRead]:
    require_moderator(db, circle_id, current_user.id)
    query = select(CircleModerationReport).where(CircleModerationReport.circle_id == circle_id)
    if not include_resolved:
        query = query.where(CircleModerationReport.status == "open")
    rows = db.scalars(query.options(
        joinedload(CircleModerationReport.reporter), joinedload(CircleModerationReport.reviewer)
    ).order_by(CircleModerationReport.created_at.desc(), CircleModerationReport.id.desc())).all()
    return [read_report(db, row) for row in rows]


@router.post("/reports/{report_id}/review", response_model=CircleModerationReportRead)
def review_report(
    circle_id: int,
    report_id: int,
    payload: CircleModerationReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CircleModerationReportRead:
    require_moderator(db, circle_id, current_user.id)
    row = db.scalar(select(CircleModerationReport).where(
        CircleModerationReport.id == report_id,
        CircleModerationReport.circle_id == circle_id,
    ).options(joinedload(CircleModerationReport.reporter), joinedload(CircleModerationReport.reviewer)))
    if not row:
        raise HTTPException(status_code=404, detail="Moderation report not found")
    if row.status != "open":
        raise HTTPException(status_code=409, detail="Moderation report is already resolved")

    target = get_target(db, circle_id, row.target_type, row.target_id)
    now = datetime.now(timezone.utc)
    row.status = "resolved"
    row.reviewed_by_user_id = current_user.id
    row.reviewed_at = now
    row.action = payload.action
    row.action_note = payload.note

    if payload.action == "hide":
        target.deleted_at = now
        db.add(target)

    db.add(row)
    db.commit()
    db.refresh(row)
    row = db.scalar(select(CircleModerationReport).where(CircleModerationReport.id == row.id).options(
        joinedload(CircleModerationReport.reporter), joinedload(CircleModerationReport.reviewer)
    ))
    return read_report(db, row)
