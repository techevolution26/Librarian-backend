from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.creator_account import CreatorAccount
from app.models.creator_book_submission import CreatorBookSubmission
from app.models.creator_rights_declaration import CreatorRightsDeclaration
from app.models.user import User
from app.schemas.creator_rights import CreatorRightsDeclarationCreate, CreatorRightsDeclarationRead

router = APIRouter(prefix="/creator/submissions", tags=["creator-rights"])


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


@router.get("/{submission_id}/rights", response_model=list[CreatorRightsDeclarationRead])
def list_rights_declarations(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CreatorRightsDeclarationRead]:
    _owned_submission(db, submission_id, current_user.id)
    return list(
        db.scalars(
            select(CreatorRightsDeclaration)
            .where(CreatorRightsDeclaration.submission_id == submission_id)
            .order_by(CreatorRightsDeclaration.version.desc())
        ).all()
    )


@router.get("/{submission_id}/rights/current", response_model=CreatorRightsDeclarationRead | None)
def get_current_rights_declaration(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorRightsDeclarationRead | None:
    _owned_submission(db, submission_id, current_user.id)
    return db.scalar(
        select(CreatorRightsDeclaration)
        .where(
            CreatorRightsDeclaration.submission_id == submission_id,
            CreatorRightsDeclaration.status == "active",
        )
        .order_by(CreatorRightsDeclaration.version.desc())
    )


@router.post("/{submission_id}/rights", response_model=CreatorRightsDeclarationRead, status_code=status.HTTP_201_CREATED)
def create_rights_declaration(
    submission_id: int,
    payload: CreatorRightsDeclarationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorRightsDeclarationRead:
    submission = _owned_submission(db, submission_id, current_user.id)
    if submission.status not in {"draft", "changes_requested"}:
        raise HTTPException(status_code=409, detail="Rights can only be declared for a draft or changes-requested submission")
    if not payload.attestation_acknowledged:
        raise HTTPException(status_code=422, detail="You must acknowledge the rights declaration attestation")

    latest_version = db.scalar(
        select(func.max(CreatorRightsDeclaration.version)).where(
            CreatorRightsDeclaration.submission_id == submission.id
        )
    ) or 0
    current = db.scalar(
        select(CreatorRightsDeclaration)
        .where(
            CreatorRightsDeclaration.submission_id == submission.id,
            CreatorRightsDeclaration.status == "active",
        )
        .order_by(CreatorRightsDeclaration.version.desc())
    )
    if current is not None:
        current.status = "superseded"

    declaration = CreatorRightsDeclaration(
        submission_id=submission.id,
        creator_account_id=submission.creator_account_id,
        version=latest_version + 1,
        rights_basis=payload.rights_basis,
        rights_holder_name=payload.rights_holder_name or submission.author_name,
        rights_statement=payload.rights_statement,
        territory=payload.territory,
        license_name=payload.license_name,
        license_url=str(payload.license_url) if payload.license_url else None,
        hosting_allowed=payload.hosting_allowed,
        public_display_allowed=payload.public_display_allowed,
        download_allowed=payload.download_allowed,
        redistribution_allowed=payload.redistribution_allowed,
        commercial_use_allowed=payload.commercial_use_allowed,
        derivative_use_allowed=payload.derivative_use_allowed,
        declaration_note=payload.declaration_note,
        attestation_text=(
            "I declare that the rights information supplied for this submission is accurate "
            "to the best of my knowledge and that I have the authority represented by this declaration."
        ),
        status="active",
        declared_by_user_id=current_user.id,
        declared_at=datetime.now(timezone.utc),
    )
    db.add(declaration)
    db.commit()
    db.refresh(declaration)
    return declaration
