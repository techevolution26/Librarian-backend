from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.authz import require_admin_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import BOOKS_STORAGE_DIR, get_storage_root
from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_metadata import ArchivalMetadata
from app.models.archival_object import ArchivalObject
from app.models.archival_provenance import ArchivalProvenance
from app.models.archival_rights import ArchivalRights
from app.models.asset_storage_location import AssetStorageLocation
from app.models.book import Book, ORIGINAL_FORMATS, RIGHTS_STATEMENTS
from app.models.book_asset import BookAsset
from app.models.preservation_event import PreservationEvent
from app.models.resource_contribution import (
    RESOURCE_CONTRIBUTION_MATERIAL_TYPES,
    RESOURCE_CONTRIBUTION_RIGHTS_BASES,
    ResourceContribution,
    ResourceContributionAsset,
)
from app.models.user import User
from app.schemas.resource_contribution import (
    ResourceContributionApprovalRead,
    ResourceContributionListRead,
    ResourceContributionMetadataUpdate,
    ResourceContributionRead,
    ResourceContributionReviewUpdate,
)
from app.services.admin_activity import log_admin_activity
from app.services.iiif_image import inspect_image
from app.services.storage import get_storage_backend
from app.services.uploads import (
    build_public_static_url,
    compute_sha256,
    generate_accession_no,
    save_upload_file,
    validate_upload_file,
)

router = APIRouter(prefix="/community/resource-contributions", tags=["community-resource-contributions"])

ARCHIVAL_OBJECT_TYPES = {"book", "manuscript", "newspaper", "photograph", "map", "document", "oral_history", "other"}


def _safe_filename(value: str | None) -> str:
    return Path(value or "upload.bin").name[:255] or "upload.bin"


def _normalize_csv(value: str) -> str:
    result: list[str] = []
    for item in value.split(","):
        clean = item.strip()
        if clean and clean.casefold() not in {existing.casefold() for existing in result}:
            result.append(clean)
    return ",".join(result)


def _contribution_query():
    return select(ResourceContribution).options(
        selectinload(ResourceContribution.assets),
        selectinload(ResourceContribution.contributor),
    )


def _owned_contribution(db: Session, contribution_id: int, user_id: int) -> ResourceContribution:
    row = db.scalar(
        _contribution_query().where(
            ResourceContribution.id == contribution_id,
            ResourceContribution.contributor_user_id == user_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Resource contribution not found")
    return row


def _read(row: ResourceContribution) -> ResourceContributionRead:
    return ResourceContributionRead.model_validate({
        "id": row.id,
        "contributor_user_id": row.contributor_user_id,
        "contributor_name": row.contributor.full_name if row.contributor else None,
        "material_type": row.material_type,
        "status": row.status,
        "title": row.title,
        "author_name": row.author_name,
        "description": row.description,
        "language": row.language,
        "genres": row.genres,
        "subjects": row.subjects,
        "original_format": row.original_format,
        "archival_object_type": row.archival_object_type,
        "origin": row.origin,
        "era": row.era,
        "condition_notes": row.condition_notes,
        "source_institution": row.source_institution,
        "source_collection": row.source_collection,
        "shelfmark": row.shelfmark,
        "provenance_accession_number": row.provenance_accession_number,
        "digitized_by": row.digitized_by,
        "digitization_method": row.digitization_method,
        "scanner_device": row.scanner_device,
        "preservation_master_format": row.preservation_master_format,
        "derivative_format": row.derivative_format,
        "software": row.software,
        "rights_statement": row.rights_statement,
        "rights_holder": row.rights_holder,
        "rights_basis": row.rights_basis,
        "rights_evidence": row.rights_evidence,
        "contributor_note": row.contributor_note,
        "review_note": row.review_note,
        "reviewed_by_user_id": row.reviewed_by_user_id,
        "reviewed_at": row.reviewed_at,
        "submitted_at": row.submitted_at,
        "imported_book_id": row.imported_book_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "assets": row.assets,
    })


@router.post("/", response_model=ResourceContributionRead, status_code=201)
async def submit_resource_contribution(
    material_type: str = Form(...),
    title: str = Form(...),
    author_name: str = Form(...),
    description: str = Form(...),
    language: str = Form("en"),
    genres: str = Form(""),
    subjects: str = Form(""),
    original_format: str = Form("born-digital"),
    archival_object_type: str = Form("document"),
    origin: str | None = Form(None),
    era: str | None = Form(None),
    condition_notes: str | None = Form(None),
    source_institution: str | None = Form(None),
    source_collection: str | None = Form(None),
    shelfmark: str | None = Form(None),
    provenance_accession_number: str | None = Form(None),
    digitized_by: str | None = Form(None),
    digitization_method: str | None = Form(None),
    scanner_device: str | None = Form(None),
    preservation_master_format: str | None = Form(None),
    derivative_format: str | None = Form(None),
    software: str | None = Form(None),
    rights_statement: str = Form("all-rights-reserved"),
    rights_holder: str | None = Form(None),
    rights_basis: str = Form("unknown"),
    rights_evidence: str | None = Form(None),
    contributor_note: str | None = Form(None),
    accuracy_attested: bool = Form(...),
    primary_file: UploadFile | None = File(None),
    canvas_files: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResourceContributionRead:
    """Accept a private user contribution; never creates a public Book directly."""
    settings = get_settings()
    material_type = material_type.strip().lower()
    original_format = original_format.strip().lower()
    archival_object_type = archival_object_type.strip().lower()
    rights_statement = rights_statement.strip().lower()
    rights_basis = rights_basis.strip().lower()

    if material_type not in RESOURCE_CONTRIBUTION_MATERIAL_TYPES:
        raise HTTPException(status_code=400, detail="material_type must be pdf, text, or facsimile")
    if original_format not in ORIGINAL_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid original_format")
    if archival_object_type not in ARCHIVAL_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported archival object type")
    if rights_statement not in RIGHTS_STATEMENTS:
        raise HTTPException(status_code=400, detail="Invalid rights_statement")
    if rights_basis not in RESOURCE_CONTRIBUTION_RIGHTS_BASES:
        raise HTTPException(status_code=400, detail="Invalid rights_basis")
    if not accuracy_attested:
        raise HTTPException(status_code=400, detail="Please confirm that the contribution details are accurate")
    if not title.strip() or not author_name.strip() or not description.strip():
        raise HTTPException(status_code=400, detail="Title, creator, and description are required")

    canvas_files = [item for item in (canvas_files or []) if item and item.filename]
    if len(canvas_files) > settings.max_archival_canvas_count:
        raise HTTPException(status_code=413, detail=f"At most {settings.max_archival_canvas_count} archival images may be submitted")
    if material_type == "pdf" and primary_file is None:
        raise HTTPException(status_code=400, detail="A PDF primary file is required")
    if material_type == "text" and primary_file is None:
        raise HTTPException(status_code=400, detail="A UTF-8 text primary file is required")
    if material_type == "facsimile" and (primary_file is not None or not canvas_files):
        raise HTTPException(status_code=400, detail="An image-only contribution requires one or more images and no primary file")
    if material_type in {"pdf", "text"} and primary_file is None:
        raise HTTPException(status_code=400, detail="A primary source file is required")

    pending_count = db.scalar(select(func.count()).select_from(ResourceContribution).where(
        ResourceContribution.contributor_user_id == current_user.id,
        ResourceContribution.status.in_(["submitted", "under_review", "changes_requested"]),
    )) or 0
    if pending_count >= settings.max_pending_resource_contributions_per_user:
        raise HTTPException(status_code=429, detail="You have reached the limit of active contributions. Wait for a review before submitting another.")

    folder = uuid4().hex
    staging_dir = get_storage_root() / "community-contributions" / folder
    saved: list[tuple[str, Path, str, str, int, str | None, int | None, int | None]] = []
    aggregate_limit = settings.max_archival_ingest_total_mb * 1024 * 1024
    try:
        if primary_file is not None:
            if material_type == "pdf":
                validate_upload_file(primary_file, {"application/pdf"}, settings.max_pdf_upload_mb, "PDF")
                filename, path = await save_upload_file(primary_file, staging_dir, "source.pdf", settings.max_pdf_upload_mb, "PDF")
                mime = "application/pdf"
                with path.open("rb") as stream:
                    if not stream.read(8).startswith(b"%PDF-"):
                        raise HTTPException(status_code=400, detail="PDF content signature is invalid")
            else:
                validate_upload_file(primary_file, {"text/plain", "text/markdown"}, settings.max_text_upload_mb, "Plain text")
                filename, path = await save_upload_file(primary_file, staging_dir, "source.txt", settings.max_text_upload_mb, "Plain text")
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    raise HTTPException(status_code=400, detail="Text source must be valid UTF-8") from exc
                if not text.strip() or "\x00" in text:
                    raise HTTPException(status_code=400, detail="Text source is empty or contains binary data")
                mime = "text/plain; charset=utf-8"
            saved.append(("primary", path, _safe_filename(primary_file.filename), mime, 0, None, None, None))

        for sequence, image in enumerate(canvas_files, start=1):
            validate_upload_file(image, {"image/jpeg", "image/png", "image/webp"}, settings.max_archival_image_upload_mb, "Archival image")
            filename, path = await save_upload_file(image, staging_dir, "canvas.jpg", settings.max_archival_image_upload_mb, "Archival image")
            try:
                info = inspect_image(path)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Image '{_safe_filename(image.filename)}' is not a valid JPEG, PNG, or WebP file") from exc
            if info.width * info.height > 100_000_000:
                raise HTTPException(status_code=413, detail=f"Image '{_safe_filename(image.filename)}' exceeds the 100-megapixel safety limit")
            mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(getattr(info, "format", None))
            if mime is None:
                raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP image content is supported")
            label = Path(_safe_filename(image.filename)).stem[:255] or f"Canvas {sequence}"
            saved.append(("canvas", path, _safe_filename(image.filename), mime, sequence, label, info.width, info.height))

        if material_type == "facsimile" and not any(item[0] == "canvas" for item in saved):
            raise HTTPException(status_code=400, detail="At least one valid archival image is required")
        if sum(item[1].stat().st_size for item in saved) > aggregate_limit:
            raise HTTPException(status_code=413, detail=f"Combined contribution exceeds {settings.max_archival_ingest_total_mb}MB")

        row = ResourceContribution(
            contributor_user_id=current_user.id,
            material_type=material_type,
            status="submitted",
            title=title.strip(),
            author_name=author_name.strip(),
            description=description.strip(),
            language=language.strip() or "en",
            genre_csv=_normalize_csv(genres),
            subjects_csv=_normalize_csv(subjects),
            original_format=original_format,
            archival_object_type=archival_object_type,
            origin=origin.strip() if origin else None,
            era=era.strip() if era else None,
            condition_notes=condition_notes.strip() if condition_notes else None,
            source_institution=source_institution.strip() if source_institution else None,
            source_collection=source_collection.strip() if source_collection else None,
            shelfmark=shelfmark.strip() if shelfmark else None,
            provenance_accession_number=provenance_accession_number.strip() if provenance_accession_number else None,
            digitized_by=digitized_by.strip() if digitized_by else None,
            digitization_method=digitization_method.strip() if digitization_method else None,
            scanner_device=scanner_device.strip() if scanner_device else None,
            preservation_master_format=preservation_master_format.strip() if preservation_master_format else None,
            derivative_format=derivative_format.strip() if derivative_format else None,
            software=software.strip() if software else None,
            rights_statement=rights_statement,
            rights_holder=rights_holder.strip() if rights_holder else None,
            rights_basis=rights_basis,
            rights_evidence=rights_evidence.strip() if rights_evidence else None,
            contributor_note=contributor_note.strip() if contributor_note else None,
            accuracy_attested_at=datetime.now(timezone.utc),
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.flush()
        for role, path, original_name, mime, sequence, label, width, height in saved:
            storage_key = path.relative_to(get_storage_root()).as_posix()
            db.add(ResourceContributionAsset(
                contribution_id=row.id,
                asset_role=role,
                sequence=sequence,
                original_filename=original_name,
                storage_key=storage_key,
                mime_type=mime,
                size_bytes=path.stat().st_size,
                checksum_sha256=compute_sha256(path),
                label=label,
                width=width,
                height=height,
            ))
        db.commit()
        row = db.scalar(_contribution_query().where(ResourceContribution.id == row.id))
        return _read(row)
    except HTTPException:
        db.rollback()
        for _, path, *_ in saved:
            path.unlink(missing_ok=True)
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
    except Exception:
        db.rollback()
        for _, path, *_ in saved:
            path.unlink(missing_ok=True)
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise


@router.get("/mine", response_model=ResourceContributionListRead)
def list_my_resource_contributions(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ResourceContributionListRead:
    stmt = _contribution_query().where(ResourceContribution.contributor_user_id == current_user.id)
    rows = db.scalars(stmt.order_by(ResourceContribution.submitted_at.desc())).all()
    return ResourceContributionListRead(items=[_read(row) for row in rows], total=len(rows))


@router.get("/admin/queue", response_model=ResourceContributionListRead)
def list_admin_resource_contributions(
    status_filter: str = Query(default="submitted", alias="status"),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ResourceContributionListRead:
    require_admin_user(current_user)
    if status_filter not in {"submitted", "under_review", "changes_requested", "rejected", "approved", "withdrawn"}:
        raise HTTPException(status_code=400, detail="Invalid contribution status filter")
    stmt = _contribution_query().where(ResourceContribution.status == status_filter)
    rows = db.scalars(stmt.order_by(ResourceContribution.submitted_at.asc())).all()
    return ResourceContributionListRead(items=[_read(row) for row in rows], total=len(rows))


@router.get("/{contribution_id}", response_model=ResourceContributionRead)
def get_resource_contribution(
    contribution_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ResourceContributionRead:
    if current_user.role == "ADMIN":
        row = db.scalar(_contribution_query().where(ResourceContribution.id == contribution_id))
    else:
        row = _owned_contribution(db, contribution_id, current_user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="Resource contribution not found")
    return _read(row)


@router.get("/{contribution_id}/assets/{asset_id}")
def read_contribution_asset(
    contribution_id: int, asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> FileResponse:
    row = db.get(ResourceContribution, contribution_id)
    if row is None or (current_user.role != "ADMIN" and row.contributor_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Resource contribution asset not found")
    asset = db.scalar(select(ResourceContributionAsset).where(
        ResourceContributionAsset.id == asset_id,
        ResourceContributionAsset.contribution_id == contribution_id,
    ))
    if asset is None:
        raise HTTPException(status_code=404, detail="Resource contribution asset not found")
    try:
        path = get_storage_backend().resolve(asset.storage_key)
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=404, detail="Contribution asset is unavailable")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Contribution asset is unavailable")
    disposition = "inline" if (asset.mime_type.startswith("image/") or asset.mime_type in {"application/pdf", "text/plain; charset=utf-8"}) else "attachment"
    return FileResponse(path, media_type=asset.mime_type, filename=asset.original_filename, content_disposition_type=disposition)


@router.patch("/{contribution_id}", response_model=ResourceContributionRead)
def update_resource_contribution_metadata(
    contribution_id: int, payload: ResourceContributionMetadataUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ResourceContributionRead:
    row = _owned_contribution(db, contribution_id, current_user.id)
    if row.status != "changes_requested":
        raise HTTPException(status_code=409, detail="Only contributions with requested changes can be edited")
    if payload.title is not None: row.title = payload.title.strip()
    if payload.author_name is not None: row.author_name = payload.author_name.strip()
    if payload.description is not None: row.description = payload.description.strip()
    if payload.language is not None: row.language = payload.language.strip()
    if payload.original_format is not None: row.original_format = payload.original_format
    if payload.archival_object_type is not None: row.archival_object_type = payload.archival_object_type
    if payload.genres is not None: row.genre_csv = _normalize_csv(",".join(payload.genres))
    if payload.subjects is not None: row.subjects_csv = _normalize_csv(",".join(payload.subjects))
    if payload.origin is not None: row.origin = payload.origin.strip() or None
    if payload.era is not None: row.era = payload.era.strip() or None
    if payload.condition_notes is not None: row.condition_notes = payload.condition_notes.strip() or None
    if payload.source_institution is not None: row.source_institution = payload.source_institution.strip() or None
    if payload.source_collection is not None: row.source_collection = payload.source_collection.strip() or None
    if payload.shelfmark is not None: row.shelfmark = payload.shelfmark.strip() or None
    if payload.provenance_accession_number is not None: row.provenance_accession_number = payload.provenance_accession_number.strip() or None
    if payload.digitized_by is not None: row.digitized_by = payload.digitized_by.strip() or None
    if payload.digitization_method is not None: row.digitization_method = payload.digitization_method.strip() or None
    if payload.scanner_device is not None: row.scanner_device = payload.scanner_device.strip() or None
    if payload.preservation_master_format is not None: row.preservation_master_format = payload.preservation_master_format.strip() or None
    if payload.derivative_format is not None: row.derivative_format = payload.derivative_format.strip() or None
    if payload.software is not None: row.software = payload.software.strip() or None
    if payload.rights_statement is not None: row.rights_statement = payload.rights_statement
    if payload.rights_holder is not None: row.rights_holder = payload.rights_holder.strip() or None
    if payload.rights_basis is not None: row.rights_basis = payload.rights_basis
    if payload.rights_evidence is not None: row.rights_evidence = payload.rights_evidence.strip() or None
    if payload.contributor_note is not None: row.contributor_note = payload.contributor_note.strip() or None
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/{contribution_id}/resubmit", response_model=ResourceContributionRead)
def resubmit_resource_contribution(
    contribution_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ResourceContributionRead:
    row = _owned_contribution(db, contribution_id, current_user.id)
    if row.status != "changes_requested":
        raise HTTPException(status_code=409, detail="Only a contribution with requested changes can be resubmitted")
    row.status = "submitted"
    row.submitted_at = datetime.now(timezone.utc)
    row.review_note = None
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/{contribution_id}/withdraw", response_model=ResourceContributionRead)
def withdraw_resource_contribution(
    contribution_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ResourceContributionRead:
    row = _owned_contribution(db, contribution_id, current_user.id)
    if row.status not in {"submitted", "changes_requested"}:
        raise HTTPException(status_code=409, detail="This contribution can no longer be withdrawn")
    row.status = "withdrawn"
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/admin/{contribution_id}/review", response_model=ResourceContributionRead)
def review_resource_contribution(
    contribution_id: int, payload: ResourceContributionReviewUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ResourceContributionRead:
    require_admin_user(current_user)
    row = db.scalar(_contribution_query().where(ResourceContribution.id == contribution_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Resource contribution not found")
    if row.status not in {"submitted", "under_review", "changes_requested"}:
        raise HTTPException(status_code=409, detail="Contribution is not in a reviewable state")
    row.status = payload.status
    row.review_note = payload.review_note.strip() if payload.review_note else None
    row.reviewed_by_user_id = current_user.id
    row.reviewed_at = datetime.now(timezone.utc)
    log_admin_activity(
        db, current_user, action=f"community.resource_contribution_{payload.status}",
        entity_type="resource_contribution", entity_id=row.id,
        metadata={"status": payload.status, "contributor_user_id": row.contributor_user_id},
    )
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/admin/{contribution_id}/approve", response_model=ResourceContributionApprovalRead)
def approve_resource_contribution(
    contribution_id: int, request: Request,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ResourceContributionApprovalRead:
    """Import reviewed source into a draft Book; Admin rights review/publish remains separate."""
    require_admin_user(current_user)
    row = db.scalar(_contribution_query().where(ResourceContribution.id == contribution_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Resource contribution not found")
    if row.status not in {"submitted", "under_review"}:
        raise HTTPException(status_code=409, detail="Only submitted or in-review contributions can be approved")
    if row.imported_book_id is not None:
        raise HTTPException(status_code=409, detail="This contribution has already been imported")

    backend = get_storage_backend()
    staged_assets = sorted(row.assets, key=lambda item: (item.sequence, item.id))
    if row.material_type in {"pdf", "text"} and not any(asset.asset_role == "primary" for asset in staged_assets):
        raise HTTPException(status_code=409, detail="The primary source file is missing")
    if row.material_type == "facsimile" and not any(asset.asset_role == "canvas" for asset in staged_assets):
        raise HTTPException(status_code=409, detail="The facsimile has no image canvases")

    created_paths: list[Path] = []
    staged_to_delete: list[Path] = []
    committed = False
    try:
        accession_no = generate_accession_no()
        book_id_folder = uuid4().hex
        primary_contribution_asset = next((asset for asset in staged_assets if asset.asset_role == "primary"), None)
        primary_filename: str | None = None
        primary_destination: Path | None = None
        primary_text: str | None = None
        primary_type: str | None = None
        primary_mime: str | None = None
        primary_checksum: str | None = None

        # Recheck file existence and fixity at the trust boundary before promotion.
        for asset in staged_assets:
            source_path = backend.resolve(asset.storage_key)
            if not source_path.is_file() or compute_sha256(source_path) != asset.checksum_sha256:
                raise HTTPException(status_code=409, detail=f"Contribution file '{asset.original_filename}' is missing or its checksum changed")

        if primary_contribution_asset is not None:
            suffix = Path(primary_contribution_asset.storage_key).suffix or (".pdf" if row.material_type == "pdf" else ".txt")
            filename = f"community-{book_id_folder}{suffix}"
            target_key = f"books/{filename}"
            backend.copy(primary_contribution_asset.storage_key, target_key)
            primary_destination = backend.resolve(target_key)
            created_paths.append(primary_destination)
            primary_filename = filename
            primary_type = "pdf" if row.material_type == "pdf" else "text"
            primary_mime = primary_contribution_asset.mime_type
            primary_checksum = primary_contribution_asset.checksum_sha256
            if row.material_type == "text":
                try:
                    primary_text = primary_destination.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    raise HTTPException(status_code=409, detail="The submitted text source is no longer valid UTF-8") from exc

        accession_no = generate_accession_no()
        placeholder = build_public_static_url("/static/assets/book-placeholder.svg", request)
        book = Book(
            title=row.title,
            author=row.author_name,
            cover=placeholder,
            description=row.description,
            rating=0,
            pages=0,
            genre_csv=row.genre_csv,
            source_type={"pdf": "pdf", "text": "text", "facsimile": "iiif"}[row.material_type],
            source_url=build_public_static_url(f"/books/file/{primary_filename}", request) if row.material_type == "pdf" and primary_filename else None,
            source_path=str(primary_destination) if primary_destination else None,
            mime_type=primary_mime,
            content_text=primary_text,
            visibility="draft",
            accession_no=accession_no,
            language=row.language,
            subjects_csv=row.subjects_csv,
            origin=row.origin,
            era=row.era,
            original_format=row.original_format,
            rights_statement=row.rights_statement,
            condition_notes=row.condition_notes,
            digitized_by=row.digitized_by,
        )
        db.add(book)
        db.flush()

        archival_object = ArchivalObject(
            identifier=f"AO-{accession_no}",
            object_type=row.archival_object_type,
            title=row.title,
            description=row.description,
            curator_user_id=current_user.id,
            visibility="draft",
        )
        db.add(archival_object)
        db.flush()
        archival_object.intellectual_metadata = ArchivalMetadata(
            language=row.language,
            subjects=row.subjects,
            genre=row.genres,
            contributors=[item.strip() for item in row.author_name.split(",") if item.strip()],
        )
        archival_object.provenance = ArchivalProvenance(
            source_institution=row.source_institution,
            source_collection=row.source_collection,
            shelfmark=row.shelfmark,
            accession_number=row.provenance_accession_number,
            original_format=row.original_format,
            physical_condition=row.condition_notes,
            origin_place=row.origin,
            digitized_by=row.digitized_by,
            digitization_method=row.digitization_method,
            scanner_device=row.scanner_device,
            master_format=row.preservation_master_format,
            derivative_format=row.derivative_format,
            software=row.software,
            notes=f"Community contribution #{row.id}. Contributor rights basis: {row.rights_basis}. Evidence supplied: {row.rights_evidence or 'None'}. {row.contributor_note or ''}".strip(),
        )
        archival_object.rights = ArchivalRights(
            rights_holder=row.rights_holder,
            rights_statement=row.rights_statement,
            view_allowed=None,
            download_allowed=False,
            redistribution_allowed=False,
            commercial_use_allowed=False,
            notes=f"Contributor declaration: {row.rights_basis}. Independent curator rights review required before any public access.",
        )
        book.archival_object = archival_object
        db.flush()

        if primary_contribution_asset is not None and primary_destination is not None and primary_filename and primary_type and primary_mime and primary_checksum:
            target_key = f"books/{primary_filename}"
            asset = BookAsset(
                book_id=book.id, asset_type=primary_type, asset_role="access", logical_key=None, version=1,
                original_filename=primary_contribution_asset.original_filename, storage_key=target_key,
                public_url=None, mime_type=primary_mime, size_bytes=primary_destination.stat().st_size,
                checksum_sha256=primary_checksum, uploaded_by=row.contributor_user_id, is_current=True,
            )
            db.add(asset)
            db.flush()
            db.add(AssetStorageLocation(
                asset_id=asset.id, provider="local", storage_key=target_key, public_url=None,
                status="active", is_primary=True, checksum_sha256=primary_checksum, size_bytes=asset.size_bytes,
            ))
            db.add(PreservationEvent(
                archival_object_id=archival_object.id, asset_id=asset.id, event_type="ingestion", outcome="success",
                agent=f"community-contributor:{row.contributor_user_id}",
                detail=f"Community contribution #{row.id} imported by Admin #{current_user.id}.",
                source_storage_key=target_key, checksum=primary_checksum, checksum_algorithm="SHA-256",
            ))
            db.add(PreservationEvent(
                archival_object_id=archival_object.id, asset_id=asset.id, event_type="checksum_generated", outcome="success",
                agent=f"community-contributor:{row.contributor_user_id}", detail="SHA-256 validated at community contribution promotion.",
                source_storage_key=target_key, checksum=primary_checksum, checksum_algorithm="SHA-256",
            ))
            primary_contribution_asset.imported_asset_id = asset.id
            staged_to_delete.append(backend.resolve(primary_contribution_asset.storage_key))
            primary_contribution_asset.storage_key = target_key

        canvas_sequence = 0
        for contribution_asset in staged_assets:
            if contribution_asset.asset_role != "canvas":
                continue
            canvas_sequence += 1
            stage_path = backend.resolve(contribution_asset.storage_key)
            suffix = stage_path.suffix or ".img"
            image_filename = f"community-canvas-{uuid4().hex}{suffix}"
            target_key = f"books/canvases/{image_filename}"
            backend.copy(contribution_asset.storage_key, target_key)
            target_path = backend.resolve(target_key)
            created_paths.append(target_path)
            if compute_sha256(target_path) != contribution_asset.checksum_sha256:
                raise HTTPException(status_code=409, detail=f"Canvas '{contribution_asset.original_filename}' failed post-copy checksum verification")
            canvas_identifier = f"tl:canvas:{uuid4().hex}"
            image_asset = BookAsset(
                book_id=book.id, asset_type="image", asset_role="access", logical_key=canvas_identifier, version=1,
                original_filename=contribution_asset.original_filename, storage_key=target_key, public_url=None,
                mime_type=contribution_asset.mime_type, size_bytes=target_path.stat().st_size,
                checksum_sha256=contribution_asset.checksum_sha256, uploaded_by=row.contributor_user_id, is_current=True,
            )
            db.add(image_asset)
            db.flush()
            db.add(AssetStorageLocation(
                asset_id=image_asset.id, provider="local", storage_key=target_key, public_url=None,
                status="active", is_primary=True, checksum_sha256=image_asset.checksum_sha256, size_bytes=image_asset.size_bytes,
            ))
            db.add(ArchivalCanvas(
                archival_object_id=archival_object.id, asset_id=image_asset.id, canvas_identifier=canvas_identifier,
                sequence=canvas_sequence, label=contribution_asset.label or f"Canvas {canvas_sequence}",
                media_type=contribution_asset.mime_type, width=contribution_asset.width, height=contribution_asset.height,
            ))
            db.add(PreservationEvent(
                archival_object_id=archival_object.id, asset_id=image_asset.id, event_type="ingestion", outcome="success",
                agent=f"community-contributor:{row.contributor_user_id}", detail=f"Community contribution #{row.id}, canvas {canvas_sequence} imported.",
                source_storage_key=target_key, checksum=image_asset.checksum_sha256, checksum_algorithm="SHA-256",
            ))
            db.add(PreservationEvent(
                archival_object_id=archival_object.id, asset_id=image_asset.id, event_type="checksum_generated", outcome="success",
                agent=f"community-contributor:{row.contributor_user_id}", detail="SHA-256 validated at community contribution promotion.",
                source_storage_key=target_key, checksum=image_asset.checksum_sha256, checksum_algorithm="SHA-256",
            ))
            contribution_asset.imported_asset_id = image_asset.id
            staged_to_delete.append(stage_path)
            contribution_asset.storage_key = target_key

        row.status = "approved"
        row.imported_book_id = book.id
        row.reviewed_by_user_id = current_user.id
        row.reviewed_at = datetime.now(timezone.utc)
        row.review_note = "Approved and imported as a draft catalogue record. Rights review and publication remain required."
        log_admin_activity(
            db, current_user, action="community.resource_contribution_approved", entity_type="resource_contribution",
            entity_id=row.id, metadata={"book_id": book.id, "archival_object_id": archival_object.id, "material_type": row.material_type},
        )
        db.commit()
        committed = True
        db.refresh(row)
        refreshed = db.scalar(_contribution_query().where(ResourceContribution.id == row.id))
        # Quarantine originals are removed only after the promoted assets and database transaction commit.
        for stage_path in staged_to_delete:
            try:
                stage_path.unlink(missing_ok=True)
            except OSError:
                # Promotion already committed. A later quarantine cleanup job can
                # remove this private duplicate without risking the imported asset.
                continue
        return ResourceContributionApprovalRead(
            contribution=_read(refreshed), book_id=book.id, archival_object_id=archival_object.id,
            book_visibility=book.visibility, rights_review_required=True,
        )
    except HTTPException:
        db.rollback()
        if not committed:
            for path in created_paths:
                path.unlink(missing_ok=True)
        raise
    except Exception:
        db.rollback()
        if not committed:
            for path in created_paths:
                path.unlink(missing_ok=True)
        raise
