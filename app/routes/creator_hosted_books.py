from __future__ import annotations


from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import get_storage_root
from app.models.asset_storage_location import AssetStorageLocation
from app.models.book import Book
from app.models.book_asset import BookAsset
from app.models.creator_account import CreatorAccount
from app.models.creator_book_submission import CreatorBookSubmission
from app.models.creator_hosted_book import CreatorHostedBook
from app.models.creator_rights_declaration import CreatorRightsDeclaration
from app.models.user import User
from app.schemas.creator_hosted_book import CreatorHostedBookRead
from app.services.uploads import compute_sha256, save_upload_file, validate_upload_file

router = APIRouter(prefix="/creator/submissions", tags=["creator-hosted-books"])


def _owned_submission(db: Session, submission_id: int, user_id: int) -> CreatorBookSubmission:
    row = db.scalar(
        select(CreatorBookSubmission)
        .join(CreatorAccount, CreatorAccount.id == CreatorBookSubmission.creator_account_id)
        .where(CreatorBookSubmission.id == submission_id, CreatorAccount.user_id == user_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return row


def _rights_for(db: Session, submission_id: int) -> CreatorRightsDeclaration:
    rights = db.scalar(
        select(CreatorRightsDeclaration)
        .where(
            CreatorRightsDeclaration.submission_id == submission_id,
            CreatorRightsDeclaration.status == "active",
        )
        .order_by(CreatorRightsDeclaration.version.desc())
    )
    if rights is None:
        raise HTTPException(status_code=409, detail="An active rights declaration is required before hosting this book")
    if not rights.hosting_allowed:
        raise HTTPException(status_code=409, detail="The active rights declaration does not allow hosting")
    return rights


def _read(db: Session, hosted: CreatorHostedBook) -> CreatorHostedBookRead:
    asset = db.scalar(
        select(BookAsset).where(
            BookAsset.book_id == hosted.book_id,
            BookAsset.asset_type == "pdf",
            BookAsset.asset_role == "access",
            BookAsset.is_current.is_(True),
        )
    )
    return CreatorHostedBookRead(
        id=hosted.id,
        submission_id=hosted.submission_id,
        creator_account_id=hosted.creator_account_id,
        book_id=hosted.book_id,
        status=hosted.status,
        title=hosted.book.title,
        author_name=hosted.book.author,
        has_access_asset=asset is not None,
        asset_id=asset.id if asset else None,
        asset_filename=asset.original_filename if asset else None,
        asset_size_bytes=asset.size_bytes if asset else None,
        asset_checksum_sha256=asset.checksum_sha256 if asset else None,
        created_at=hosted.created_at,
        updated_at=hosted.updated_at,
    )


def _owned_hosted(db: Session, submission_id: int, user_id: int) -> CreatorHostedBook:
    _owned_submission(db, submission_id, user_id)
    row = db.scalar(
        select(CreatorHostedBook).where(CreatorHostedBook.submission_id == submission_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Hosted book not found")
    return row


@router.get("/{submission_id}/hosted-book", response_model=CreatorHostedBookRead)
def get_hosted_book(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorHostedBookRead:
    return _read(db, _owned_hosted(db, submission_id, current_user.id))


@router.post("/{submission_id}/hosted-book", response_model=CreatorHostedBookRead, status_code=status.HTTP_201_CREATED)
def create_hosted_book(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorHostedBookRead:
    submission = _owned_submission(db, submission_id, current_user.id)
    if submission.creator_account.status != "active":
        raise HTTPException(status_code=403, detail="Suspended creator accounts cannot host books")
    if submission.status not in {"draft", "submitted", "under_review", "changes_requested"}:
        raise HTTPException(status_code=409, detail="This submission cannot be hosted in its current state")
    _rights_for(db, submission.id)

    existing = db.scalar(select(CreatorHostedBook).where(CreatorHostedBook.submission_id == submission.id))
    if existing is not None:
        return _read(db, existing)

    book = Book(
        title=submission.title,
        author=submission.author_name,
        cover="",
        description=submission.description,
        rating=0,
        pages=0,
        source_type="pdf",
        source_url=None,
        source_path=None,
        mime_type="application/pdf",
        content_text=None,
        visibility="draft",
        language=submission.language,
        rights_statement="restricted",
        original_format="born-digital",
    )
    book.genres = submission.genres
    db.add(book)
    db.flush()

    hosted = CreatorHostedBook(
        submission_id=submission.id,
        creator_account_id=submission.creator_account_id,
        book_id=book.id,
        status="draft",
    )
    db.add(hosted)
    db.commit()
    db.refresh(hosted)
    return _read(db, hosted)


@router.post("/{submission_id}/hosted-book/file", response_model=CreatorHostedBookRead)
async def upload_hosted_book_file(
    submission_id: int,
    pdf_file: UploadFile | None = File(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreatorHostedBookRead:
    submission = _owned_submission(db, submission_id, current_user.id)
    _rights_for(db, submission.id)
    if submission.creator_account.status != "active":
        raise HTTPException(status_code=403, detail="Suspended creator accounts cannot host books")
    if submission.status not in {"draft", "submitted", "under_review", "changes_requested"}:
        raise HTTPException(status_code=409, detail="This submission cannot receive a hosted file in its current state")

    hosted = db.scalar(select(CreatorHostedBook).where(CreatorHostedBook.submission_id == submission.id))
    if hosted is None:
        raise HTTPException(status_code=404, detail="Create the hosted book before uploading its file")

    upload = pdf_file or file
    if upload is None:
        raise HTTPException(status_code=400, detail="A PDF file is required")

    settings = get_settings()
    validate_upload_file(upload, {"application/pdf"}, settings.max_pdf_upload_mb, "PDF")

    destination_dir = get_storage_root() / "creator-hosted" / str(submission.creator_account_id) / str(submission.id)
    filename, destination = await save_upload_file(
        upload,
        destination_dir=destination_dir,
        fallback_filename="book.pdf",
        max_size_mb=settings.max_pdf_upload_mb,
        label="PDF",
    )
    storage_root = get_storage_root().resolve()
    storage_key = destination.resolve().relative_to(storage_root).as_posix()
    checksum = compute_sha256(destination)
    size = destination.stat().st_size

    current_assets = db.scalars(
        select(BookAsset).where(
            BookAsset.book_id == hosted.book_id,
            BookAsset.asset_type == "pdf",
            BookAsset.asset_role == "access",
            BookAsset.is_current.is_(True),
        )
    ).all()
    next_version = max(
        db.scalars(
            select(BookAsset.version).where(
                BookAsset.book_id == hosted.book_id,
                BookAsset.asset_type == "pdf",
                BookAsset.asset_role == "access",
            )
        ).all() or [0]
    ) + 1

    for old in current_assets:
        old.is_current = False

    asset = BookAsset(
        book_id=hosted.book_id,
        asset_type="pdf",
        asset_role="access",
        version=next_version,
        original_filename=upload.filename or filename,
        storage_key=storage_key,
        public_url=None,
        mime_type="application/pdf",
        size_bytes=size,
        checksum_sha256=checksum,
        uploaded_by=current_user.id,
        is_current=True,
    )
    db.add(asset)
    db.flush()
    db.add(AssetStorageLocation(
        asset_id=asset.id,
        provider="local",
        storage_key=storage_key,
        public_url=None,
        status="active",
        is_primary=True,
        checksum_sha256=checksum,
        size_bytes=size,
    ))
    hosted.status = "hosted"
    hosted.book.source_path = str(destination)
    hosted.book.mime_type = "application/pdf"
    hosted.book.source_type = "pdf"
    hosted.book.source_url = None
    hosted.book.checksum_sha256 = checksum
    hosted.book.visibility = "draft"

    try:
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise

    db.refresh(hosted)
    return _read(db, hosted)
