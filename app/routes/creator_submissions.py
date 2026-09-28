from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.authz import require_admin_user
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.creator_account import CreatorAccount
from app.models.creator_book_submission import CreatorBookSubmission
from app.models.creator_rights_declaration import CreatorRightsDeclaration
from app.models.user import User
from app.schemas.creator_submissions import (
    CreatorBookSubmissionCreate,
    CreatorBookSubmissionListRead,
    CreatorBookSubmissionRead,
    CreatorBookSubmissionUpdate,
    CreatorSubmissionReviewUpdate,
)

router = APIRouter(prefix="/creator/submissions", tags=["creator-submissions"])


def _account_for_user(db: Session, user_id: int) -> CreatorAccount:
    account = db.scalar(select(CreatorAccount).where(CreatorAccount.user_id == user_id))
    if account is None:
        raise HTTPException(status_code=404, detail="Creator account not found")
    if account.status != "active":
        raise HTTPException(status_code=403, detail="Creator account is not active")
    return account


def _owned_submission(db: Session, submission_id: int, user_id: int) -> CreatorBookSubmission:
    row = db.scalar(
        select(CreatorBookSubmission)
        .join(CreatorAccount, CreatorAccount.id == CreatorBookSubmission.creator_account_id)
        .where(
            CreatorBookSubmission.id == submission_id,
            CreatorAccount.user_id == user_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return row


def _normalize_genres(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        clean = value.strip()
        if clean and clean not in result:
            result.append(clean)
    return result


@router.get("/", response_model=CreatorBookSubmissionListRead)
def list_my_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorBookSubmissionListRead:
    account = _account_for_user(db, current_user.id)
    base = select(CreatorBookSubmission).where(CreatorBookSubmission.creator_account_id == account.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(CreatorBookSubmission.created_at.desc())).all()
    return CreatorBookSubmissionListRead(items=rows, total=total)


@router.post("/", response_model=CreatorBookSubmissionRead, status_code=201)
def create_submission(
    payload: CreatorBookSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorBookSubmissionRead:
    account = _account_for_user(db, current_user.id)
    row = CreatorBookSubmission(
        creator_account_id=account.id,
        title=payload.title.strip(),
        author_name=payload.author_name.strip(),
        description=payload.description.strip(),
        language=payload.language.strip(),
        creator_note=payload.creator_note.strip() if payload.creator_note else None,
        status="draft",
    )
    row.genres = _normalize_genres(payload.genres)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{submission_id}", response_model=CreatorBookSubmissionRead)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorBookSubmissionRead:
    return _owned_submission(db, submission_id, current_user.id)


@router.patch("/{submission_id}", response_model=CreatorBookSubmissionRead)
def update_submission(
    submission_id: int,
    payload: CreatorBookSubmissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorBookSubmissionRead:
    row = _owned_submission(db, submission_id, current_user.id)
    if row.status not in {"draft", "changes_requested"}:
        raise HTTPException(status_code=409, detail="Only draft or changes-requested submissions can be edited")

    if payload.title is not None:
        row.title = payload.title.strip()
    if payload.author_name is not None:
        row.author_name = payload.author_name.strip()
    if payload.description is not None:
        row.description = payload.description.strip()
    if payload.language is not None:
        row.language = payload.language.strip()
    if payload.genres is not None:
        row.genres = _normalize_genres(payload.genres)
    if "creator_note" in payload.model_fields_set:
        row.creator_note = payload.creator_note.strip() if payload.creator_note else None

    db.commit()
    db.refresh(row)
    return row


@router.post("/{submission_id}/submit", response_model=CreatorBookSubmissionRead)
def submit_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorBookSubmissionRead:
    row = _owned_submission(db, submission_id, current_user.id)
    if row.status not in {"draft", "changes_requested"}:
        raise HTTPException(status_code=409, detail="Submission is not ready to be submitted")

    if not row.title.strip() or not row.author_name.strip() or not row.description.strip():
        raise HTTPException(status_code=422, detail="Title, author name, and description are required")

    rights = db.scalar(
        select(CreatorRightsDeclaration).where(
            CreatorRightsDeclaration.submission_id == row.id,
            CreatorRightsDeclaration.status == "active",
        )
    )
    if rights is None:
        raise HTTPException(
            status_code=409,
            detail="An active rights declaration is required before submitting this book for review",
        )

    row.status = "submitted"
    row.submitted_at = datetime.now(timezone.utc)
    row.review_note = None
    row.reviewed_at = None
    row.reviewed_by_user_id = None
    db.commit()
    db.refresh(row)
    return row


@router.get("/admin/queue", response_model=CreatorBookSubmissionListRead)
def admin_submission_queue(
    status_filter: str = Query(default="submitted", alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorBookSubmissionListRead:
    require_admin_user(current_user)
    if status_filter not in {"submitted", "under_review", "changes_requested"}:
        raise HTTPException(status_code=400, detail="Invalid submission status")
    stmt = select(CreatorBookSubmission).where(CreatorBookSubmission.status == status_filter)
    rows = db.scalars(stmt.order_by(CreatorBookSubmission.submitted_at.asc())).all()
    return CreatorBookSubmissionListRead(items=rows, total=len(rows))


@router.post("/admin/{submission_id}/review", response_model=CreatorBookSubmissionRead)
def review_submission(
    submission_id: int,
    payload: CreatorSubmissionReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorBookSubmissionRead:
    require_admin_user(current_user)
    row = db.get(CreatorBookSubmission, submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if row.status not in {"submitted", "under_review"}:
        raise HTTPException(status_code=409, detail="Submission is not awaiting review")

    row.status = payload.status
    row.review_note = payload.review_note.strip() if payload.review_note else None
    row.reviewed_at = datetime.now(timezone.utc)
    row.reviewed_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return row
