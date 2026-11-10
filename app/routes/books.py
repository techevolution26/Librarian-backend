import os
import math
import shutil
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, Query, status
from sqlalchemy import select, case, func, or_
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from app.models.library_item import LibraryItem
from app.core.database import get_db
from app.core.storage import BOOKS_STORAGE_DIR, COVERS_STORAGE_DIR, build_public_file_url, ensure_storage_dirs
from app.models.book import Book, RIGHTS_STATEMENTS, ORIGINAL_FORMATS
from app.models.book_asset import BookAsset
from app.models.asset_storage_location import AssetStorageLocation
from app.models.archival_object import ArchivalObject
from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_metadata import ArchivalMetadata
from app.models.archival_provenance import ArchivalProvenance
from app.models.archival_rights import ArchivalRights
from app.models.preservation_event import PreservationEvent
from app.schemas.book import BookContentRead, BookRead, AdminBookListRead, BookFacets, AssetStorageLocationRead
from app.models.user import User
from app.core.authz import require_admin_user
from app.core.security import get_current_user, get_optional_current_user

from app.services.admin_activity import log_admin_activity
from app.services.entitlements import resolve_book_access
from app.models.admin_activity_log import AdminActivityLog
from app.services.iiif_image import IIIFImageInfo, inspect_image
from app.services.uploads import (
    validate_upload_file,
    save_upload_file,
    build_public_static_url,
    compute_sha256,
    generate_accession_no,
)
from app.core.config import get_settings

router = APIRouter(prefix="/books", tags=["books"])

ensure_storage_dirs()


def to_resource_read(row: Book, *, include_assets: bool = False) -> BookRead:

    return BookRead(
        id=row.id,
        title=row.title,
        author=row.author,
        authors=row.authors,
        cover=row.cover,
        description=row.description,
        rating=row.rating,
        pages=row.pages,
        genre=row.genres,
        tags=row.tags,
        source_type=row.source_type,
        content_type=row.content_type,
        source_url=row.source_url,
        mime_type=row.mime_type,
        visibility=getattr(row, "visibility", "published"),
        archived_at=getattr(row, "archived_at", None),
        archival_object_id=getattr(row, "archival_object_id", None),
        cover_path=getattr(row, "cover_path", None),
        is_featured=getattr(row, "is_featured", False),
        accession_no=getattr(row, "accession_no", None),
        language=getattr(row, "language", "en"),
        subjects=getattr(row, "subjects", []),
        origin=getattr(row, "origin", None),
        era=getattr(row, "era", None),
        original_format=getattr(row, "original_format", "born-digital"),
        rights_statement=getattr(row, "rights_statement", "all-rights-reserved"),
        condition_notes=getattr(row, "condition_notes", None),
        curator_note=getattr(row, "curator_note", None),
        checksum_sha256=getattr(row, "checksum_sha256", None),
        digitized_by=getattr(row, "digitized_by", None),
        digitized_at=getattr(row, "digitized_at", None),
        assets=list(getattr(row, "assets", [])) if include_assets else [],
    )


to_book_read = to_resource_read


def _archival_view_allowed(book: Book) -> bool:
    """Legacy books without an archival authority record keep their old access path.

    Once a Book is linked to an ArchivalObject, the explicit archival rights
    decision becomes authoritative for delivery of the underlying digital
    material. Missing or unverified decisions fail closed.
    """
    archival_object = book.archival_object
    if archival_object is None:
        return True
    rights = archival_object.rights
    return bool(rights and rights.view_allowed is True and rights.verified_at is not None)


def _safe_archive_identifier(accession_no: str) -> str:
    return f"AO-{accession_no}"


def _image_mime_type(image_info: IIIFImageInfo) -> str:
    """Return the decoded image format, never infer media type from filename suffix."""
    formats = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
    mime_type = formats.get(getattr(image_info, "format", None))
    if mime_type is None:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP image content is supported")
    return mime_type


def _withdraw_current_access_asset(
    db: Session,
    *,
    asset: BookAsset,
    archival_object: ArchivalObject | None,
    current_user: User,
    detail: str,
) -> None:
    """Retain an old asset version, mark it non-current, and record its withdrawal."""
    if not asset.is_current:
        return
    asset.is_current = False
    if archival_object is None:
        return
    db.add(PreservationEvent(
        archival_object_id=archival_object.id,
        asset_id=asset.id,
        event_type="access_withdrawn",
        outcome="success",
        agent=current_user.full_name or f"user:{current_user.id}",
        detail=detail,
        source_storage_key=asset.storage_key,
        checksum=asset.checksum_sha256,
        checksum_algorithm="SHA-256",
    ))


def _asset_version(db: Session, *, book_id: int, asset_type: str, logical_key: str | None) -> int:
    query = select(func.max(BookAsset.version)).where(
        BookAsset.book_id == book_id,
        BookAsset.asset_type == asset_type,
        BookAsset.asset_role == "access",
    )
    if logical_key is None:
        query = query.where(BookAsset.logical_key.is_(None))
    else:
        query = query.where(BookAsset.logical_key == logical_key)
    return int(db.scalar(query) or 0) + 1


def _add_asset_storage_location(db: Session, asset: BookAsset) -> None:
    db.add(AssetStorageLocation(
        asset_id=asset.id,
        provider="local",
        storage_key=asset.storage_key,
        public_url=asset.public_url,
        status="active",
        is_primary=True,
        checksum_sha256=asset.checksum_sha256,
        size_bytes=asset.size_bytes,
    ))


def _invalidate_archival_rights_review(archival_object: ArchivalObject, book: Book) -> None:
    """Withdraw public access after the source set changes until rights are reviewed again."""
    if archival_object.rights is None:
        archival_object.rights = ArchivalRights()
    archival_object.rights.view_allowed = None
    archival_object.rights.verified_at = None
    archival_object.rights.verified_by = None
    archival_object.rights.download_allowed = False
    archival_object.rights.redistribution_allowed = False
    archival_object.rights.commercial_use_allowed = False
    archival_object.visibility = "draft"
    book.visibility = "draft"


def _ensure_archival_object_for_book(book: Book, current_user: User) -> ArchivalObject:
    archival_object = book.archival_object
    if archival_object is not None:
        return archival_object

    accession_no = book.accession_no or generate_accession_no()
    book.accession_no = accession_no
    archival_object = ArchivalObject(
        identifier=_safe_archive_identifier(accession_no),
        object_type="document",
        title=book.title,
        description=book.description,
        curator_user_id=current_user.id,
        visibility="draft",
    )
    archival_object.intellectual_metadata = ArchivalMetadata(
        language=book.language,
        subjects=book.subjects,
        genre=book.genres,
        contributors=[item.strip() for item in book.author.split(",") if item.strip()],
    )
    archival_object.provenance = ArchivalProvenance(
        original_format=book.original_format,
        physical_condition=book.condition_notes,
        origin_place=book.origin,
        digitized_by=book.digitized_by,
        digitized_at=book.digitized_at,
    )
    archival_object.rights = ArchivalRights(
        rights_statement=book.rights_statement,
        view_allowed=None,
        download_allowed=False,
        redistribution_allowed=False,
        commercial_use_allowed=False,
    )
    book.archival_object = archival_object
    return archival_object

def public_books_stmt():
    return (
        select(Book)
        .where(Book.archived_at.is_(None))
        .where(Book.visibility == "published")
    )



@router.get("/file/{filename:path}")
def serve_book_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> FileResponse:
    """Serve a book PDF only after the authoritative access decision."""
    relative = Path(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise HTTPException(status_code=404, detail="Book file not found")

    candidate = (BOOKS_STORAGE_DIR / relative).resolve()
    storage_root = BOOKS_STORAGE_DIR.resolve()
    if storage_root not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Book file not found")

    book = db.scalar(select(Book).where(Book.source_path == str(candidate)))
    if book is None:
        raise HTTPException(status_code=404, detail="Book file not found")
    if not _archival_view_allowed(book):
        raise HTTPException(status_code=403, detail="Archival rights review does not permit digital viewing")

    if current_user is None:
        allowed, reason, _ = resolve_book_access(db, user_id=0, book_id=book.id)
    else:
        allowed, reason, _ = resolve_book_access(db, user_id=current_user.id, book_id=book.id)
    if not allowed:
        status_code = status.HTTP_401_UNAUTHORIZED if current_user is None and reason == "entitlement_required" else status.HTTP_403_FORBIDDEN
        raise HTTPException(
            status_code=status_code,
            detail={"code": reason, "message": "Book access is required to read this title."},
        )

    return FileResponse(candidate, media_type=book.mime_type or "application/pdf")


@router.get("/admin/list", response_model=AdminBookListRead)
def admin_list_books(
    q: str | None = None,
    visibility: str = "all",
    status: str = "all",
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AdminBookListRead:
    require_admin_user(current_user)

    stmt = select(Book)

    if q and q.strip():
        pattern = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Book.title).like(pattern),
                func.lower(Book.author).like(pattern),
                func.lower(Book.description).like(pattern),
            )
        )

    if visibility != "all":
        if visibility not in {"published", "draft"}:
            raise HTTPException(status_code=400, detail="Invalid visibility")
        stmt = stmt.where(Book.visibility == visibility)

    if status == "active":
        stmt = stmt.where(Book.archived_at.is_(None))
    elif status == "archived":
        stmt = stmt.where(Book.archived_at.is_not(None))
    elif status != "all":
        raise HTTPException(status_code=400, detail="Invalid status")

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    pages = max(math.ceil(total / limit), 1)
    safe_page = min(page, pages)
    offset = (safe_page - 1) * limit

    rows = db.scalars(
        stmt.order_by(Book.id.desc()).offset(offset).limit(limit)
    ).all()

    return AdminBookListRead(
        items=[to_book_read(row) for row in rows],
        total=total,
        page=safe_page,
        limit=limit,
        pages=pages,
    )


@router.post("/admin/{book_id}/assets/{asset_id}/preservation-master", response_model=BookRead)
def create_preservation_master(
    book_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    """Create an explicit preservation-master copy from an existing asset.

    This never relabels an access asset. The source remains unchanged and the
    new master receives its own BookAsset identity, storage key, checksum,
    storage location, and append-only preservation event.
    """
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    source = db.scalar(
        select(BookAsset).where(
            BookAsset.id == asset_id,
            BookAsset.book_id == book_id,
        )
    )
    if not source:
        raise HTTPException(status_code=404, detail="Source asset not found")

    if source.asset_role == "preservation_master":
        raise HTTPException(status_code=400, detail="Source asset is already a preservation master")

    existing_master = db.scalar(
        select(BookAsset).where(
            BookAsset.book_id == book_id,
            BookAsset.asset_type == source.asset_type,
            BookAsset.asset_role == "preservation_master",
            BookAsset.is_current.is_(True),
        )
    )
    if existing_master:
        raise HTTPException(
            status_code=409,
            detail="A current preservation master already exists for this asset type",
        )

    try:
        from app.services.storage import get_storage_backend
        resolved_source = get_storage_backend().resolve(source.storage_key)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if not resolved_source.is_file():
        raise HTTPException(status_code=409, detail="Source asset is not available in physical storage")

    master_dir = BOOKS_STORAGE_DIR / "preservation-masters" / str(book_id)
    master_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(source.original_filename).suffix.lower() or ".bin"
    filename = f"{uuid4().hex}{suffix}"
    destination = master_dir / filename
    shutil.copy2(resolved_source, destination)

    checksum = compute_sha256(destination)
    if checksum.lower() != source.checksum_sha256.lower():
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="Preservation copy checksum does not match source asset")

    previous_version = db.scalar(
        select(func.max(BookAsset.version)).where(
            BookAsset.book_id == book_id,
            BookAsset.asset_type == source.asset_type,
            BookAsset.asset_role == "preservation_master",
        )
    ) or 0

    master = BookAsset(
        book_id=book_id,
        asset_type=source.asset_type,
        asset_role="preservation_master",
        version=previous_version + 1,
        original_filename=source.original_filename,
        storage_key=f"books/preservation-masters/{book_id}/{filename}",
        public_url=None,
        mime_type=source.mime_type,
        size_bytes=destination.stat().st_size,
        checksum_sha256=checksum,
        uploaded_by=current_user.id,
        is_current=True,
        source_asset_id=source.id,
        derivation_type="preservation_copy",
    )
    db.add(master)
    db.flush()

    db.add(AssetStorageLocation(
        asset_id=master.id,
        provider="local",
        storage_key=master.storage_key,
        public_url=None,
        status="active",
        is_primary=True,
        checksum_sha256=checksum,
        size_bytes=master.size_bytes,
    ))

    object_id = db.scalar(select(Book.archival_object_id).where(Book.id == book_id))
    if object_id is not None:
        db.add(PreservationEvent(
            archival_object_id=object_id,
            asset_id=master.id,
            event_type="preservation_master_created",
            event_date=datetime.now(timezone.utc),
            outcome="success",
            agent=current_user.full_name or f"user:{current_user.id}",
            detail=f"Preservation master created from asset {source.id} with verified SHA-256 match.",
            source_storage_key=source.storage_key,
            target_storage_key=master.storage_key,
            checksum=checksum,
            checksum_algorithm="SHA-256",
        ))

    log_admin_activity(
        db,
        current_user,
        action="book.preservation_master_created",
        entity_type="book_asset",
        entity_id=master.id,
        metadata={
            "book_id": book_id,
            "source_asset_id": source.id,
            "asset_type": source.asset_type,
            "version": master.version,
        },
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise

    db.refresh(book)
    return to_resource_read(book, include_assets=True)


@router.get(
    "/admin/{book_id}/assets/{asset_id}/storage-locations",
    response_model=list[AssetStorageLocationRead],
)
def list_asset_storage_locations(
    book_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetStorageLocationRead]:
    """Return the physical storage copies recorded for one logical asset."""
    require_admin_user(current_user)

    asset = db.scalar(
        select(BookAsset).where(BookAsset.id == asset_id, BookAsset.book_id == book_id)
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return list(
        db.scalars(
            select(AssetStorageLocation)
            .where(AssetStorageLocation.asset_id == asset.id)
            .order_by(AssetStorageLocation.is_primary.desc(), AssetStorageLocation.created_at.asc())
        ).all()
    )


@router.post(
    "/admin/{book_id}/assets/{asset_id}/replicas",
    response_model=AssetStorageLocationRead,
)
def replicate_asset(
    book_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetStorageLocationRead:
    """Create and verify a physical replica of a logical archival asset.

    T3 deliberately supports the configured local backend only. The replica
    is still recorded through the storage-location abstraction so a future
    object-storage backend can implement the same operation without changing
    BookAsset identity or the preservation model.
    """
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    asset = db.scalar(
        select(BookAsset).where(BookAsset.id == asset_id, BookAsset.book_id == book_id)
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    source_location = db.scalar(
        select(AssetStorageLocation)
        .where(
            AssetStorageLocation.asset_id == asset.id,
            AssetStorageLocation.status == "active",
        )
        .order_by(AssetStorageLocation.is_primary.desc(), AssetStorageLocation.created_at.asc())
    )
    if not source_location:
        raise HTTPException(status_code=409, detail="No active physical storage location is available")

    if source_location.provider != "local":
        raise HTTPException(
            status_code=409,
            detail=f"Replication provider '{source_location.provider}' has no copy implementation yet",
        )

    from app.services.storage import get_storage_backend

    try:
        backend = get_storage_backend()
        source_path = backend.resolve(source_location.storage_key)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if not source_path.is_file():
        source_location.status = "unavailable"
        source_location.replication_error = "Source storage object is not available"
        source_location.replication_status = "failed"
        db.commit()
        raise HTTPException(status_code=409, detail="Source asset is not available in physical storage")

    replica_key = f"books/replicas/{book_id}/{asset.id}/{uuid4().hex}{Path(asset.original_filename).suffix.lower() or '.bin'}"
    replica = AssetStorageLocation(
        asset_id=asset.id,
        provider=source_location.provider,
        bucket=source_location.bucket,
        storage_key=replica_key,
        public_url=None,
        status="active",
        is_primary=False,
        replicated_from_location_id=source_location.id,
        replication_status="copying",
    )
    db.add(replica)
    db.flush()

    target_created = False
    try:
        backend.copy(source_location.storage_key, replica_key)
        target_created = True
        target_path = backend.resolve(replica_key)
        checksum = compute_sha256(target_path)
        size_bytes = target_path.stat().st_size

        if checksum.lower() != asset.checksum_sha256.lower():
            raise ValueError("Replica checksum does not match the logical asset checksum")
        if size_bytes != asset.size_bytes:
            raise ValueError("Replica size does not match the logical asset size")

        replica.checksum_sha256 = checksum
        replica.size_bytes = size_bytes
        replica.verified_at = datetime.now(timezone.utc)
        replica.replication_status = "verified"
        replica.replication_error = None

        object_id = db.scalar(select(Book.archival_object_id).where(Book.id == book_id))
        if object_id is not None:
            db.add(PreservationEvent(
                archival_object_id=object_id,
                asset_id=asset.id,
                event_type="storage_replication",
                event_date=datetime.now(timezone.utc),
                outcome="success",
                agent=current_user.full_name or f"user:{current_user.id}",
                detail=(
                    f"Verified replica created from storage location {source_location.id}; "
                    "SHA-256 and size match the logical asset."
                ),
                source_storage_key=source_location.storage_key,
                target_storage_key=replica_key,
                checksum=checksum,
                checksum_algorithm="SHA-256",
            ))

        log_admin_activity(
            db,
            current_user,
            action="book.asset_replicated",
            entity_type="book_asset",
            entity_id=asset.id,
            metadata={
                "book_id": book_id,
                "asset_id": asset.id,
                "source_location_id": source_location.id,
                "replica_location_id": replica.id,
                "provider": replica.provider,
                "replication_status": replica.replication_status,
            },
        )
        db.commit()
        db.refresh(replica)
        return replica
    except Exception as exc:
        db.rollback()
        replica = db.get(AssetStorageLocation, replica.id)
        if replica is None:
            replica = AssetStorageLocation(
                asset_id=asset.id,
                provider=source_location.provider,
                bucket=source_location.bucket,
                storage_key=replica_key,
                public_url=None,
                status="retired",
                is_primary=False,
                replicated_from_location_id=source_location.id,
                replication_status="failed",
                replication_error=str(exc),
            )
            db.add(replica)
        else:
            replica.status = "retired"
            replica.replication_status = "failed"
            replica.replication_error = str(exc)

        object_id = db.scalar(select(Book.archival_object_id).where(Book.id == book_id))
        if object_id is not None:
            db.add(PreservationEvent(
                archival_object_id=object_id,
                asset_id=asset.id,
                event_type="storage_replication",
                event_date=datetime.now(timezone.utc),
                outcome="failure",
                agent=current_user.full_name or f"user:{current_user.id}",
                detail=f"Storage replication failed: {exc}",
                source_storage_key=source_location.storage_key,
                target_storage_key=replica_key,
                checksum=None,
                checksum_algorithm="SHA-256",
            ))
        db.commit()
        if target_created:
            try:
                backend.resolve(replica_key).unlink(missing_ok=True)
            except Exception:
                pass
        raise HTTPException(status_code=409, detail=f"Storage replication failed: {exc}") from exc


@router.get("/admin/activity")
def list_admin_activity(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin_user(current_user)

    rows = db.scalars(
        select(AdminActivityLog)
        .order_by(AdminActivityLog.created_at.desc(), AdminActivityLog.id.desc())
        .limit(limit)
    ).all()

    return [
        {
            "id": row.id,
            "admin_user_id": row.admin_user_id,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "metadata": row.metadata_json,
            "created_at": row.created_at,
        }
        for row in rows
    ]



@router.get("/admin/{book_id}", response_model=BookRead)
def admin_get_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    row = db.scalar(select(Book).where(Book.id == book_id))

    if not row:
        raise HTTPException(status_code=404, detail="Book not found")

    return to_resource_read(row, include_assets=True)



@router.get("/featured", response_model=BookRead)
def get_featured_book(db: Session = Depends(get_db)) -> BookRead:
    manual_featured = db.scalar(
        public_books_stmt()
        .where(Book.is_featured.is_(True))
        .order_by(Book.id.desc())
        .limit(1)
    )

    if manual_featured:
        return to_book_read(manual_featured)

    since = datetime.now(timezone.utc) - timedelta(days=30)

    featured_score = (
        func.coalesce(func.avg(Book.rating), 0) * 2
        + func.coalesce(func.count(LibraryItem.id), 0)
        + func.coalesce(
            func.sum(
                case(
                    (LibraryItem.status == "reading", 5),
                    (LibraryItem.status == "saved", 3),
                    (LibraryItem.status == "finished", 4),
                    else_=1,
                )
            ),
            0,
        )
    ).label("featured_score")

    row = db.scalar(
        public_books_stmt()
        .outerjoin(
            LibraryItem,
            (LibraryItem.book_id == Book.id)
            & (LibraryItem.updated_at >= since),
        )
        .group_by(Book.id)
        .order_by(
            featured_score.desc(),
            Book.rating.desc(),
            Book.pages.desc(),
            Book.id.desc(),
        )
        .limit(1)
    )

    if not row:
        raise HTTPException(status_code=404, detail="No featured book found")

    return to_book_read(row)


@router.get("/trending", response_model=list[BookRead])
def list_trending_books(
    limit: int = 12,
    db: Session = Depends(get_db),
) -> list[BookRead]:
    since = datetime.now(timezone.utc) - timedelta(days=14)

    trending_score = (
        func.count(LibraryItem.id) * 2
        + func.coalesce(
            func.sum(
                case(
                    (LibraryItem.status == "reading", 5),
                    (LibraryItem.status == "saved", 3),
                    (LibraryItem.status == "finished", 4),
                    else_=1,
                )
            ),
            0,
        )
        + func.coalesce(func.avg(Book.rating), 0)
    ).label("trending_score")

    rows = db.scalars(
        public_books_stmt()
        .outerjoin(
            LibraryItem,
            (LibraryItem.book_id == Book.id)
            & (LibraryItem.updated_at >= since),
        )
        .group_by(Book.id)
        .order_by(trending_score.desc(), Book.rating.desc(), Book.id.desc())
        .limit(limit)
    ).all()

    return [to_book_read(row) for row in rows]


@router.get("/recommended", response_model=list[BookRead])
def recommended_books(
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BookRead]:
    """Return deterministic, explainable recommendations from user taste + behavior.

    This is intentionally a ranking system, not an ML claim. Explicit onboarding
    preferences provide the strongest signal; the user's reading behavior and
    archive-wide engagement provide smaller supporting signals. Books already in
    the user's library are excluded.
    """
    settings = current_user.settings
    preferred_genres = {value.strip().lower() for value in (settings.preferred_genres or [])} if settings else set()
    goals = {value.strip().lower() for value in (settings.reading_goals or [])} if settings else set()
    styles = {value.strip().lower() for value in (settings.content_styles or [])} if settings else set()
    lengths = {value.strip().lower() for value in (settings.preferred_lengths or [])} if settings else set()

    library_rows = db.scalars(
        select(LibraryItem).where(LibraryItem.user_id == current_user.id)
    ).all()
    library_ids = {row.book_id for row in library_rows}

    # Reading behavior is used as evidence about the kinds of books the user
    # actually engages with. Finished > reading > saved, but all are modest.
    behavior_genres: dict[str, float] = {}
    for row in library_rows:
        book = db.get(Book, row.book_id)
        if not book:
            continue
        weight = {"finished": 3.0, "reading": 2.0, "saved": 1.0}.get(row.status, 0.5)
        for genre in book.genres:
            key = genre.strip().lower()
            if key:
                behavior_genres[key] = behavior_genres.get(key, 0.0) + weight

    candidates = db.scalars(public_books_stmt()).all()
    if not candidates:
        return []

    # Archive-wide popularity is deliberately a tie-break/supporting signal.
    library_counts = dict(
        db.query(LibraryItem.book_id, func.count(LibraryItem.id))
        .group_by(LibraryItem.book_id)
        .all()
    )

    def length_matches(book: Book) -> float:
        pages = book.pages or 0
        if not lengths:
            return 0.0
        score = 0.0
        for value in lengths:
            if "short" in value and pages <= 180:
                score += 1.0
            elif "medium" in value and 180 < pages <= 350:
                score += 1.0
            elif "deep" in value and pages > 350:
                score += 1.0
        return score

    def text_matches(book: Book, vocabulary: set[str]) -> float:
        if not vocabulary:
            return 0.0
        haystack = " ".join([
            book.title,
            book.description,
            *book.genres,
            *book.tags,
            *book.subjects,
        ]).lower()
        return sum(1.0 for value in vocabulary if value and value in haystack)

    scored: list[tuple[float, Book]] = []
    for book in candidates:
        if book.id in library_ids:
            continue

        genres = {value.strip().lower() for value in book.genres}
        explicit_genre = len(genres & preferred_genres)
        behavior_score = sum(behavior_genres.get(genre, 0.0) for genre in genres)
        goal_score = text_matches(book, goals)
        style_score = text_matches(book, styles)
        length_score = length_matches(book)
        popularity = min(float(library_counts.get(book.id, 0)), 10.0)
        rating = float(book.rating or 0.0)
        featured = 1.0 if getattr(book, "is_featured", False) else 0.0

        score = (
            explicit_genre * 12.0
            + behavior_score * 2.0
            + goal_score * 4.0
            + style_score * 3.0
            + length_score * 3.0
            + popularity * 0.5
            + rating * 0.4
            + featured * 0.5
        )
        scored.append((score, book))

    scored.sort(key=lambda item: (item[0], item[1].rating or 0, item[1].id), reverse=True)
    return [to_book_read(book) for _, book in scored[:limit]]


@router.get("/discover", response_model=list[BookRead])
def discover_books(
    q: str | None = None,
    genre: str = "All",
    subject: str = "All",
    language: str = "All",
    original_format: str = "All",
    era: str = "All",
    sort: str = "recommended",
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[BookRead]:
    stmt = public_books_stmt()

    if q:
        pattern = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Book.title).like(pattern),
                func.lower(Book.author).like(pattern),
                func.lower(Book.description).like(pattern),
            )
        )

    rows = db.scalars(stmt).all()

    if genre and genre.lower() != "all":
        rows = [
            book
            for book in rows
            if any(item.lower() == genre.lower() for item in book.genres)
        ]

    if subject and subject.lower() != "all":
        rows = [
            book
            for book in rows
            if any(item.lower() == subject.lower() for item in book.subjects)
        ]

    if language and language.lower() != "all":
        rows = [book for book in rows if book.language.lower() == language.lower()]

    if original_format and original_format.lower() != "all":
        rows = [
            book
            for book in rows
            if book.original_format.lower() == original_format.lower()
        ]

    if era and era.lower() != "all":
        rows = [book for book in rows if (book.era or "").lower() == era.lower()]

    if sort == "top-rated":
        rows.sort(key=lambda book: (book.rating or 0, book.id), reverse=True)
    elif sort == "newest":
        rows.sort(key=lambda book: book.id, reverse=True)
    elif sort == "featured":
        rows.sort(
            key=lambda book: (
                1 if getattr(book, "is_featured", False) else 0,
                book.rating or 0,
                book.id,
            ),
            reverse=True,
        )
    else:
        rows.sort(key=lambda book: (book.rating or 0, book.id), reverse=True)

    rows = rows[offset : offset + limit]

    return [to_book_read(row) for row in rows]



@router.get("/genres", response_model=list[str])
def list_book_genres(db: Session = Depends(get_db)) -> list[str]:
    rows = db.scalars(select(Book)).all()

    genres: set[str] = set()
    for book in rows:
        for genre in book.genres:
            genres.add(genre)

    return ["All", *sorted(genres)]


@router.get("/facets", response_model=BookFacets)
def list_book_facets(db: Session = Depends(get_db)) -> BookFacets:
    """Vocabulary currently in use across published books, for building
    faceted-search filter chips (genre/subject/language/era/format) the way
    an archive catalog exposes its browsable facets."""
    rows = db.scalars(public_books_stmt()).all()

    genres: set[str] = set()
    subjects: set[str] = set()
    languages: set[str] = set()
    eras: set[str] = set()
    formats: set[str] = set()

    for book in rows:
        genres.update(book.genres)
        subjects.update(book.subjects)
        languages.add(book.language)
        if book.era:
            eras.add(book.era)
        formats.add(book.original_format)

    return BookFacets(
        genres=sorted(genres),
        subjects=sorted(subjects),
        languages=sorted(languages),
        eras=sorted(eras),
        original_formats=sorted(formats),
        rights_statements=sorted(RIGHTS_STATEMENTS),
    )


@router.get("/", response_model=list[BookRead])
def list_books(db: Session = Depends(get_db)) -> list[BookRead]:
    rows = db.scalars(
        public_books_stmt().order_by(Book.id.desc())
    ).all()

    return [to_book_read(row) for row in rows]


@router.get("/{book_id}", response_model=BookRead)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookRead:
    row = db.scalar(
        public_books_stmt().where(Book.id == book_id)
    )

    if not row:
        raise HTTPException(status_code=404, detail="Book not found")

    return to_book_read(row)


@router.patch("/{book_id}/feature", response_model=BookRead)
def set_featured_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.archived_at is not None:
        raise HTTPException(status_code=400, detail="Archived books cannot be featured")

    if book.visibility != "published":
        raise HTTPException(status_code=400, detail="Only published books can be featured")

    db.query(Book).update({Book.is_featured: False})
    book.is_featured = True

    log_admin_activity(
        db,
        current_user,
        action="book.featured",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title},
    )

    db.commit()
    db.refresh(book)

    return to_book_read(book)


@router.patch("/{book_id}/unfeature", response_model=BookRead)
def unset_featured_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.is_featured = False

    log_admin_activity(
        db,
        current_user,
        action="book.unfeatured",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title},
    )

    db.commit()
    db.refresh(book)

    return to_book_read(book)


@router.get("/discover/stats")
def discover_stats(
    q: str | None = None,
    genre: str = "All",
    db: Session = Depends(get_db),
) -> dict[str, int]:
    rows = discover_books(q=q, genre=genre, sort="recommended", limit=100, offset=0, db=db)

    categories = {
        genre_item
        for book in rows
        for genre_item in book.genre
    }

    return {
        "visible_books": len(rows),
        "top_rated": len([book for book in rows if book.rating >= 4.5]),
        "new_this_week": min(len(rows), 6),
        "categories": len(categories),
    }


@router.get("/{book_id}/content", response_model=BookContentRead)
def get_book_content(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> BookContentRead:
    row = db.scalar(
        public_books_stmt().where(Book.id == book_id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")
    if not _archival_view_allowed(row):
        raise HTTPException(status_code=403, detail={"code": "archival_rights_review_required", "message": "The digital material is unavailable until its archival viewing rights have been reviewed and approved."})

    if current_user is None:
        allowed, reason, _ = resolve_book_access(db, user_id=0, book_id=book_id)
    else:
        allowed, reason, _ = resolve_book_access(db, user_id=current_user.id, book_id=book_id)
    if not allowed:
        status_code = status.HTTP_401_UNAUTHORIZED if current_user is None and reason == "entitlement_required" else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail={"code": reason, "message": "Book access is required to read this title."})

    return BookContentRead(
        id=row.id,
        title=row.title,
        source_type=row.source_type,
        content_type=row.content_type,
        mime_type=row.mime_type,
        source_url=row.source_url,
        content_text=row.content_text,
    )




@router.post("/ingest", response_model=BookRead, status_code=201)
async def ingest_archival_material(
    request: Request,
    material_type: str = Form(...),
    title: str = Form(...),
    author: str = Form(...),
    description: str = Form(...),
    rating: float = Form(0),
    pages: int = Form(0),
    genre_csv: str = Form(""),
    subjects_csv: str = Form(""),
    language: str = Form("en"),
    origin: str | None = Form(None),
    era: str | None = Form(None),
    original_format: str = Form("born-digital"),
    condition_notes: str | None = Form(None),
    curator_note: str | None = Form(None),
    digitized_by: str | None = Form(None),
    rights_statement: str = Form("all-rights-reserved"),
    rights_decision: str = Form("pending"),
    rights_holder: str | None = Form(None),
    rights_source: str | None = Form(None),
    rights_notes: str | None = Form(None),
    archival_object_type: str = Form("document"),
    source_institution: str | None = Form(None),
    source_collection: str | None = Form(None),
    shelfmark: str | None = Form(None),
    provenance_accession_number: str | None = Form(None),
    digitization_method: str | None = Form(None),
    scanner_device: str | None = Form(None),
    preservation_master_format: str | None = Form(None),
    derivative_format: str | None = Form(None),
    software: str | None = Form(None),
    pdf_file: UploadFile | None = File(None),
    text_file: UploadFile | None = File(None),
    canvas_files: list[UploadFile] | None = File(None),
    cover_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    """Create a draft catalogue record and linked archival object from supported source material.

    The main representation is exactly one of PDF, UTF-8 plain text, or an
    image-only IIIF facsimile. Any of these can include supplementary image
    canvases. All files and metadata are committed together or rolled back.
    """
    require_admin_user(current_user)
    material_type = material_type.strip().lower()
    archival_object_type = archival_object_type.strip().lower()
    rights_decision = rights_decision.strip().lower()
    if material_type not in {"pdf", "text", "facsimile"}:
        raise HTTPException(status_code=400, detail="material_type must be pdf, text, or facsimile")
    if archival_object_type not in {"book", "manuscript", "newspaper", "photograph", "map", "document", "oral_history", "other"}:
        raise HTTPException(status_code=400, detail="Unsupported archival object type")
    if rights_decision not in {"pending", "allow", "deny"}:
        raise HTTPException(status_code=400, detail="rights_decision must be pending, allow, or deny")
    if rights_decision == "allow" and not (rights_source and rights_source.strip()):
        raise HTTPException(status_code=400, detail="An evidence source is required before approving online viewing")
    if original_format not in ORIGINAL_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid original_format")
    if rights_statement not in RIGHTS_STATEMENTS:
        raise HTTPException(status_code=400, detail="Invalid rights_statement")
    if not title.strip() or not author.strip() or not description.strip():
        raise HTTPException(status_code=400, detail="Title, author, and description are required")

    canvas_files = [item for item in (canvas_files or []) if item and item.filename]
    settings = get_settings()
    if len(canvas_files) > settings.max_archival_canvas_count:
        raise HTTPException(status_code=413, detail=f"At most {settings.max_archival_canvas_count} archival images may be ingested at once")

    if material_type == "pdf" and (pdf_file is None or text_file is not None):
        raise HTTPException(status_code=400, detail="Select exactly one PDF as the primary material")
    if material_type == "text" and (text_file is None or pdf_file is not None):
        raise HTTPException(status_code=400, detail="Select exactly one UTF-8 text file as the primary material")
    if material_type == "facsimile" and (pdf_file is not None or text_file is not None or not canvas_files):
        raise HTTPException(status_code=400, detail="An image-only facsimile requires one or more archival images and no PDF/text primary file")
    if material_type != "facsimile" and not (pdf_file or text_file):
        raise HTTPException(status_code=400, detail="A primary source file is required")
    if not (pdf_file or text_file or canvas_files):
        raise HTTPException(status_code=400, detail="At least one supported digital source is required")

    saved_paths: list[Path] = []
    try:
        primary_filename: str | None = None
        primary_destination: Path | None = None
        primary_mime: str | None = None
        primary_checksum: str | None = None
        primary_text: str | None = None

        if pdf_file is not None:
            validate_upload_file(pdf_file, {"application/pdf"}, settings.max_pdf_upload_mb, "PDF")
            primary_filename, primary_destination = await save_upload_file(
                pdf_file, BOOKS_STORAGE_DIR, "source.pdf", settings.max_pdf_upload_mb, "PDF"
            )
            saved_paths.append(primary_destination)
            primary_mime = "application/pdf"
            primary_checksum = compute_sha256(primary_destination)

        if text_file is not None:
            validate_upload_file(text_file, {"text/plain", "text/markdown"}, settings.max_text_upload_mb, "Plain text")
            primary_filename, primary_destination = await save_upload_file(
                text_file, BOOKS_STORAGE_DIR, "source.txt", settings.max_text_upload_mb, "Plain text"
            )
            saved_paths.append(primary_destination)
            try:
                primary_text = primary_destination.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise HTTPException(status_code=400, detail="Text source must be valid UTF-8. No lossy conversion was applied.") from exc
            if not primary_text.strip() or "\x00" in primary_text:
                raise HTTPException(status_code=400, detail="Text source is empty or contains binary data")
            primary_mime = "text/plain; charset=utf-8"
            primary_checksum = compute_sha256(primary_destination)

        cover_filename: str | None = None
        cover_destination: Path | None = None
        cover_url: str | None = None
        if cover_file is not None and cover_file.filename:
            validate_upload_file(cover_file, {"image/jpeg", "image/png", "image/webp"}, settings.max_cover_upload_mb, "Cover")
            cover_filename, cover_destination = await save_upload_file(
                cover_file, COVERS_STORAGE_DIR, "cover.jpg", settings.max_cover_upload_mb, "Cover"
            )
            saved_paths.append(cover_destination)
            try:
                inspect_image(cover_destination)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Cover file is not a valid supported image") from exc
            cover_url = build_public_static_url(f"/static/covers/{cover_filename}", request)

        prepared_canvases: list[tuple[str, str, Path, str, str, int, int, str]] = []
        for index, image_file in enumerate(canvas_files, start=1):
            validate_upload_file(
                image_file,
                {"image/jpeg", "image/png", "image/webp"},
                settings.max_archival_image_upload_mb,
                "Archival image",
            )
            image_name, image_destination = await save_upload_file(
                image_file,
                BOOKS_STORAGE_DIR / "canvases",
                "canvas.jpg",
                settings.max_archival_image_upload_mb,
                "Archival image",
            )
            saved_paths.append(image_destination)
            try:
                image_info = inspect_image(image_destination)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Image '{image_file.filename}' is not a valid supported image") from exc
            if image_info.width * image_info.height > 100_000_000:
                raise HTTPException(status_code=413, detail=f"Image '{image_file.filename}' exceeds the 100-megapixel safety limit")
            mime_type = _image_mime_type(image_info)
            label = Path(image_file.filename or image_name).stem.strip() or f"Canvas {index}"
            canvas_identifier = f"tl:canvas:{uuid4().hex}"
            prepared_canvases.append((image_file.filename or image_name, image_name, image_destination, mime_type, label[:255], image_info.width, image_info.height, canvas_identifier))

        aggregate_limit = settings.max_archival_ingest_total_mb * 1024 * 1024
        aggregate_size = sum(path.stat().st_size for path in saved_paths)
        if aggregate_size > aggregate_limit:
            raise HTTPException(status_code=413, detail=f"Combined archival ingest exceeds {settings.max_archival_ingest_total_mb}MB")

        accession_no = generate_accession_no()
        cover_value = cover_url or build_public_static_url("/static/assets/book-placeholder.svg", request)
        source_path = str(primary_destination) if primary_destination else None
        source_url = (
            build_public_static_url(f"/books/file/{primary_filename}", request)
            if material_type == "pdf" and primary_filename
            else None
        )
        book = Book(
            title=title.strip(),
            author=author.strip(),
            cover=cover_value,
            description=description.strip(),
            rating=max(0, min(float(rating), 5)),
            pages=max(0, int(pages)),
            source_type={"pdf": "pdf", "text": "text", "facsimile": "iiif"}[material_type],
            source_url=source_url,
            source_path=source_path,
            mime_type=primary_mime,
            content_text=primary_text,
            visibility="draft",
            accession_no=accession_no,
            language=language.strip() or "en",
            origin=origin.strip() if origin and origin.strip() else None,
            era=era.strip() if era and era.strip() else None,
            original_format=original_format,
            rights_statement=rights_statement,
            condition_notes=condition_notes,
            curator_note=curator_note,
            digitized_by=digitized_by,
            digitized_at=datetime.now(timezone.utc),
            checksum_sha256=primary_checksum,
        )
        book.genres = [value.strip() for value in genre_csv.split(",") if value.strip()]
        book.subjects = [value.strip() for value in subjects_csv.split(",") if value.strip()]
        db.add(book)
        db.flush()

        archival_object = ArchivalObject(
            identifier=_safe_archive_identifier(accession_no),
            object_type=archival_object_type,
            title=book.title,
            description=book.description,
            curator_user_id=current_user.id,
            visibility="draft",
        )
        archival_object.intellectual_metadata = ArchivalMetadata(
            language=book.language,
            subjects=book.subjects,
            genre=book.genres,
            contributors=[item.strip() for item in book.author.split(",") if item.strip()],
        )
        archival_object.provenance = ArchivalProvenance(
            source_institution=source_institution.strip() if source_institution and source_institution.strip() else None,
            source_collection=source_collection.strip() if source_collection and source_collection.strip() else None,
            shelfmark=shelfmark.strip() if shelfmark and shelfmark.strip() else None,
            accession_number=provenance_accession_number.strip() if provenance_accession_number and provenance_accession_number.strip() else accession_no,
            original_format=original_format,
            physical_condition=condition_notes,
            origin_place=origin.strip() if origin and origin.strip() else None,
            digitized_by=digitized_by.strip() if digitized_by and digitized_by.strip() else None,
            digitized_at=datetime.now(timezone.utc),
            digitization_method=digitization_method.strip() if digitization_method and digitization_method.strip() else None,
            scanner_device=scanner_device.strip() if scanner_device and scanner_device.strip() else None,
            master_format=preservation_master_format.strip() if preservation_master_format and preservation_master_format.strip() else None,
            derivative_format=derivative_format.strip() if derivative_format and derivative_format.strip() else None,
            software=software.strip() if software and software.strip() else None,
        )
        archival_object.rights = ArchivalRights(
            rights_statement=rights_statement,
            rights_holder=rights_holder.strip() if rights_holder and rights_holder.strip() else None,
            rights_source=rights_source.strip() if rights_source and rights_source.strip() else None,
            notes=rights_notes.strip() if rights_notes and rights_notes.strip() else None,
            view_allowed=True if rights_decision == "allow" else False if rights_decision == "deny" else None,
            download_allowed=False,
            redistribution_allowed=False,
            commercial_use_allowed=False,
            verified_at=datetime.now(timezone.utc) if rights_decision != "pending" else None,
            verified_by=(current_user.full_name or f"user:{current_user.id}") if rights_decision != "pending" else None,
        )
        db.add(archival_object)
        db.flush()
        book.archival_object = archival_object

        if primary_destination is not None and primary_filename is not None and primary_mime is not None and primary_checksum is not None:
            asset_type = "pdf" if material_type == "pdf" else "text"
            asset = BookAsset(
                book_id=book.id,
                asset_type=asset_type,
                asset_role="access",
                logical_key=None,
                version=1,
                original_filename=(pdf_file.filename if pdf_file else text_file.filename) or primary_filename,
                storage_key=f"books/{primary_filename}",
                public_url=source_url,
                mime_type=primary_mime,
                size_bytes=primary_destination.stat().st_size,
                checksum_sha256=primary_checksum,
                uploaded_by=current_user.id,
                is_current=True,
            )
            db.add(asset)
            db.flush()
            _add_asset_storage_location(db, asset)
            db.add(PreservationEvent(
                archival_object_id=archival_object.id, asset_id=asset.id, event_type="ingestion",
                outcome="success", agent=current_user.full_name or f"user:{current_user.id}",
                detail=f"Primary {asset_type} access representation ingested and SHA-256 recorded.",
                source_storage_key=asset.storage_key, checksum=asset.checksum_sha256, checksum_algorithm="SHA-256",
            ))
            db.add(PreservationEvent(
                archival_object_id=archival_object.id, asset_id=asset.id, event_type="checksum_generated",
                outcome="success", agent=current_user.full_name or f"user:{current_user.id}",
                detail="SHA-256 checksum generated at ingestion.", source_storage_key=asset.storage_key,
                checksum=asset.checksum_sha256, checksum_algorithm="SHA-256",
            ))

        for sequence, (original_filename, image_name, image_destination, mime_type, label, width, height, canvas_identifier) in enumerate(prepared_canvases, start=1):
            image_asset = BookAsset(
                book_id=book.id,
                asset_type="image",
                asset_role="access",
                logical_key=canvas_identifier,
                version=1,
                original_filename=original_filename,
                storage_key=f"books/canvases/{image_name}",
                public_url=None,
                mime_type=mime_type,
                size_bytes=image_destination.stat().st_size,
                checksum_sha256=compute_sha256(image_destination),
                uploaded_by=current_user.id,
                is_current=True,
            )
            db.add(image_asset)
            db.flush()
            _add_asset_storage_location(db, image_asset)
            db.add(PreservationEvent(
                archival_object_id=archival_object.id, asset_id=image_asset.id, event_type="ingestion",
                outcome="success", agent=current_user.full_name or f"user:{current_user.id}",
                detail=f"Archival image canvas {sequence} ingested and SHA-256 recorded.",
                source_storage_key=image_asset.storage_key, checksum=image_asset.checksum_sha256, checksum_algorithm="SHA-256",
            ))
            db.add(PreservationEvent(
                archival_object_id=archival_object.id, asset_id=image_asset.id, event_type="checksum_generated",
                outcome="success", agent=current_user.full_name or f"user:{current_user.id}",
                detail="SHA-256 checksum generated at ingestion.", source_storage_key=image_asset.storage_key,
                checksum=image_asset.checksum_sha256, checksum_algorithm="SHA-256",
            ))
            db.add(ArchivalCanvas(
                archival_object_id=archival_object.id,
                asset_id=image_asset.id,
                canvas_identifier=canvas_identifier,
                sequence=sequence,
                page_number=None,
                label=label,
                media_type=mime_type,
                width=width,
                height=height,
            ))

        if cover_destination is not None and cover_filename is not None and cover_url:
            cover_asset = BookAsset(
                book_id=book.id,
                asset_type="cover",
                asset_role="access",
                logical_key=None,
                version=1,
                original_filename=cover_file.filename or cover_filename,
                storage_key=f"covers/{cover_filename}",
                public_url=cover_url,
                mime_type={".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(Path(cover_filename).suffix.lower(), "application/octet-stream"),
                size_bytes=cover_destination.stat().st_size,
                checksum_sha256=compute_sha256(cover_destination),
                uploaded_by=current_user.id,
                is_current=True,
            )
            db.add(cover_asset)
            db.flush()
            _add_asset_storage_location(db, cover_asset)
            book.cover_path = str(cover_destination)

        log_admin_activity(
            db,
            current_user,
            action="book.archival_material_ingested",
            entity_type="book",
            entity_id=book.id,
            metadata={
                "title": book.title,
                "material_type": material_type,
                "canvas_count": len(prepared_canvases),
                "rights_decision": rights_decision,
                "archival_object_id": archival_object.id,
            },
        )
        db.commit()
        db.refresh(book)
        return to_resource_read(book, include_assets=True)
    except HTTPException:
        db.rollback()
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise
    except Exception:
        db.rollback()
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise


@router.post("/{book_id}/canvases", response_model=BookRead, status_code=201)
async def add_archival_canvases_to_book(
    book_id: int,
    image_files: list[UploadFile] = File(...),
    label_prefix: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    """Append one or more scanned images as independently versioned IIIF canvases."""
    require_admin_user(current_user)
    book = db.scalar(select(Book).where(Book.id == book_id, Book.archived_at.is_(None)))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    settings = get_settings()
    images = [item for item in image_files if item and item.filename]
    if not images:
        raise HTTPException(status_code=400, detail="Choose at least one archival image")
    existing_canvas_count = int(db.scalar(
        select(func.count(ArchivalCanvas.id)).join(ArchivalObject, ArchivalCanvas.archival_object_id == ArchivalObject.id)
        .where(ArchivalObject.book.has(Book.id == book.id))
    ) or 0) if book.archival_object_id else 0
    if existing_canvas_count + len(images) > settings.max_archival_canvas_count:
        raise HTTPException(status_code=413, detail=f"This archival object may contain at most {settings.max_archival_canvas_count} canvases")

    saved_paths: list[Path] = []
    try:
        archival_object = _ensure_archival_object_for_book(book, current_user)
        db.add(archival_object)
        db.flush()
        next_sequence = int(db.scalar(
            select(func.max(ArchivalCanvas.sequence)).where(ArchivalCanvas.archival_object_id == archival_object.id)
        ) or 0) + 1

        for offset, image_file in enumerate(images):
            validate_upload_file(
                image_file, {"image/jpeg", "image/png", "image/webp"},
                settings.max_archival_image_upload_mb, "Archival image",
            )
            image_name, image_destination = await save_upload_file(
                image_file, BOOKS_STORAGE_DIR / "canvases", "canvas.jpg",
                settings.max_archival_image_upload_mb, "Archival image",
            )
            saved_paths.append(image_destination)
            try:
                image_info = inspect_image(image_destination)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Image '{image_file.filename}' is not a valid supported image") from exc
            if image_info.width * image_info.height > 100_000_000:
                raise HTTPException(status_code=413, detail=f"Image '{image_file.filename}' exceeds the 100-megapixel safety limit")

            mime_type = _image_mime_type(image_info)
            canvas_identifier = f"tl:canvas:{uuid4().hex}"
            image_asset = BookAsset(
                book_id=book.id, asset_type="image", asset_role="access",
                logical_key=canvas_identifier, version=1,
                original_filename=image_file.filename or image_name,
                storage_key=f"books/canvases/{image_name}", public_url=None,
                mime_type=mime_type, size_bytes=image_destination.stat().st_size,
                checksum_sha256=compute_sha256(image_destination),
                uploaded_by=current_user.id, is_current=True,
            )
            db.add(image_asset)
            db.flush()
            _add_asset_storage_location(db, image_asset)
            db.add(PreservationEvent(
                archival_object_id=archival_object.id, asset_id=image_asset.id, event_type="ingestion",
                outcome="success", agent=current_user.full_name or f"user:{current_user.id}",
                detail=f"Additional archival canvas ingested as sequence {next_sequence + offset}.",
                source_storage_key=image_asset.storage_key, checksum=image_asset.checksum_sha256, checksum_algorithm="SHA-256",
            ))
            db.add(PreservationEvent(
                archival_object_id=archival_object.id, asset_id=image_asset.id, event_type="checksum_generated",
                outcome="success", agent=current_user.full_name or f"user:{current_user.id}",
                detail="SHA-256 checksum generated at canvas ingestion.", source_storage_key=image_asset.storage_key,
                checksum=image_asset.checksum_sha256, checksum_algorithm="SHA-256",
            ))
            label = Path(image_file.filename or image_name).stem.strip() or f"Canvas {next_sequence + offset}"
            if label_prefix and label_prefix.strip():
                label = f"{label_prefix.strip()} {next_sequence + offset}"
            db.add(ArchivalCanvas(
                archival_object_id=archival_object.id, asset_id=image_asset.id,
                canvas_identifier=canvas_identifier, sequence=next_sequence + offset,
                page_number=None, label=label[:255], media_type=mime_type,
                width=image_info.width, height=image_info.height,
            ))

        aggregate_limit = settings.max_archival_ingest_total_mb * 1024 * 1024
        current_access_size = int(db.scalar(select(func.coalesce(func.sum(BookAsset.size_bytes), 0)).where(
            BookAsset.book_id == book.id, BookAsset.asset_role == "access", BookAsset.is_current.is_(True),
        )) or 0)
        # The query runs after each new asset was flushed, so it already includes
        # the newly added files. Do not add saved_paths a second time.
        if current_access_size > aggregate_limit:
            raise HTTPException(status_code=413, detail=f"Combined archival assets may not exceed {settings.max_archival_ingest_total_mb}MB")

        _invalidate_archival_rights_review(archival_object, book)
        log_admin_activity(
            db, current_user, action="book.archival_canvases_added",
            entity_type="book", entity_id=book.id,
            metadata={"canvas_count": len(images), "archival_object_id": archival_object.id, "rights_review_invalidated": True},
        )
        db.commit()
        db.refresh(book)
        return to_resource_read(book, include_assets=True)
    except HTTPException:
        db.rollback()
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise
    except Exception:
        db.rollback()
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise


@router.patch("/{book_id}/canvases/{canvas_id}/image", response_model=BookRead)
async def replace_archival_canvas_image(
    book_id: int,
    canvas_id: int,
    image_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    """Create a new version for a canvas while retaining its stable identifier."""
    require_admin_user(current_user)
    book = db.scalar(select(Book).where(Book.id == book_id, Book.archived_at.is_(None)))
    if not book or not book.archival_object:
        raise HTTPException(status_code=404, detail="Book or linked archival object not found")
    archival_object = book.archival_object
    if current_user.id != archival_object.curator_user_id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="You are not allowed to modify this archival object")
    canvas = db.scalar(select(ArchivalCanvas).where(
        ArchivalCanvas.id == canvas_id, ArchivalCanvas.archival_object_id == archival_object.id,
    ))
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")

    settings = get_settings()
    validate_upload_file(image_file, {"image/jpeg", "image/png", "image/webp"}, settings.max_archival_image_upload_mb, "Archival image")
    saved_path: Path | None = None
    try:
        image_name, image_destination = await save_upload_file(
            image_file, BOOKS_STORAGE_DIR / "canvases", "canvas.jpg",
            settings.max_archival_image_upload_mb, "Archival image",
        )
        saved_path = image_destination
        try:
            image_info = inspect_image(image_destination)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Replacement is not a valid supported image") from exc
        if image_info.width * image_info.height > 100_000_000:
            raise HTTPException(status_code=413, detail="Image exceeds the 100-megapixel safety limit")

        current_asset = db.scalar(select(BookAsset).where(
            BookAsset.id == canvas.asset_id, BookAsset.book_id == book.id,
        )) if canvas.asset_id else None
        aggregate_limit = settings.max_archival_ingest_total_mb * 1024 * 1024
        current_access_size = int(db.scalar(select(func.coalesce(func.sum(BookAsset.size_bytes), 0)).where(
            BookAsset.book_id == book.id,
            BookAsset.asset_role == "access",
            BookAsset.is_current.is_(True),
        )) or 0)
        previous_size = current_asset.size_bytes if current_asset and current_asset.is_current else 0
        replacement_size = image_destination.stat().st_size
        if current_access_size - previous_size + replacement_size > aggregate_limit:
            raise HTTPException(
                status_code=413,
                detail=f"Combined archival assets may not exceed {settings.max_archival_ingest_total_mb}MB",
            )
        if current_asset:
            _withdraw_current_access_asset(
                db, asset=current_asset, archival_object=archival_object, current_user=current_user,
                detail=f"Canvas {canvas.canvas_identifier} image version withdrawn after replacement.",
            )
        version = _asset_version(db, book_id=book.id, asset_type="image", logical_key=canvas.canvas_identifier)
        mime_type = _image_mime_type(image_info)
        replacement = BookAsset(
            book_id=book.id, asset_type="image", asset_role="access",
            logical_key=canvas.canvas_identifier, version=version,
            original_filename=image_file.filename or image_name,
            storage_key=f"books/canvases/{image_name}", public_url=None,
            mime_type=mime_type, size_bytes=image_destination.stat().st_size,
            checksum_sha256=compute_sha256(image_destination), uploaded_by=current_user.id, is_current=True,
            source_asset_id=current_asset.id if current_asset else None,
            derivation_type="replacement",
        )
        db.add(replacement)
        db.flush()
        _add_asset_storage_location(db, replacement)
        db.add(PreservationEvent(
            archival_object_id=archival_object.id, asset_id=replacement.id, event_type="ingestion",
            outcome="success", agent=current_user.full_name or f"user:{current_user.id}",
            detail=f"Canvas {canvas.canvas_identifier} received asset version {version}.",
            source_storage_key=replacement.storage_key, checksum=replacement.checksum_sha256, checksum_algorithm="SHA-256",
        ))
        canvas.asset_id = replacement.id
        canvas.media_type = mime_type
        canvas.width = image_info.width
        canvas.height = image_info.height
        _invalidate_archival_rights_review(archival_object, book)
        log_admin_activity(
            db, current_user, action="archival_canvas.image_replaced",
            entity_type="archival_canvas", entity_id=canvas.id,
            metadata={"book_id": book.id, "asset_id": replacement.id, "version": version, "rights_review_invalidated": True},
        )
        db.commit()
        db.refresh(book)
        return to_resource_read(book, include_assets=True)
    except HTTPException:
        db.rollback()
        if saved_path:
            saved_path.unlink(missing_ok=True)
        raise
    except Exception:
        db.rollback()
        if saved_path:
            saved_path.unlink(missing_ok=True)
        raise


@router.post("/upload-pdf", response_model=BookRead, status_code=201)
async def upload_pdf_book(
    request: Request,
    title: str = Form(...),
    author: str = Form(...),
    cover: str | None = Form(None),
    description: str = Form(...),
    rating: float = Form(0),
    pages: int = Form(0),
    genre_csv: str = Form(""),
    subjects_csv: str = Form(""),
    language: str = Form("en"),
    origin: str | None = Form(None),
    era: str | None = Form(None),
    original_format: str = Form("born-digital"),
    rights_statement: str = Form("all-rights-reserved"),
    condition_notes: str | None = Form(None),
    curator_note: str | None = Form(None),
    digitized_by: str | None = Form(None),
    visibility: str = Form("draft"),
    pdf_file: UploadFile | None = File(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    settings = get_settings()

    if original_format not in ORIGINAL_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid original_format")
    if rights_statement not in RIGHTS_STATEMENTS:
        raise HTTPException(status_code=400, detail="Invalid rights_statement")
    if visibility not in {"draft", "published"}:
        raise HTTPException(status_code=400, detail="Invalid visibility")

    validate_upload_file(
        pdf_file,
        allowed_content_types={"application/pdf"},
        max_size_mb=settings.max_pdf_upload_mb,
        label="PDF",
    )

    filename, destination = await save_upload_file(
        pdf_file,
        destination_dir=BOOKS_STORAGE_DIR,
        fallback_filename="book.pdf",
        max_size_mb=settings.max_pdf_upload_mb,
        label="PDF",
    )

    source_url = build_public_static_url(f"/books/file/{filename}", request)

    cover_url = cover or build_public_static_url("/static/assets/book-placeholder.svg", request)

    book = Book(
        title=title,
        author=author,
        cover=cover_url,
        description=description,
        rating=rating,
        pages=pages,
        source_type="pdf",
        source_url=source_url,
        source_path=str(destination),
        mime_type="application/pdf",
        content_text=None,
        visibility=visibility,
        accession_no=generate_accession_no(),
        language=language,
        origin=origin,
        era=era,
        original_format=original_format,
        rights_statement=rights_statement,
        condition_notes=condition_notes,
        curator_note=curator_note,
        digitized_by=digitized_by,
        digitized_at=datetime.now(timezone.utc),
        checksum_sha256=compute_sha256(destination),
    )
    book.genres = [g.strip() for g in genre_csv.split(",") if g.strip()]
    book.subjects = [s.strip() for s in subjects_csv.split(",") if s.strip()]

    db.add(book)
    db.flush()

    asset = BookAsset(
        book_id=book.id,
        asset_type="pdf",
        asset_role="access",
        version=1,
        original_filename=pdf_file.filename or filename,
        storage_key=f"books/{filename}",
        public_url=source_url,
        mime_type="application/pdf",
        size_bytes=destination.stat().st_size,
        checksum_sha256=book.checksum_sha256 or compute_sha256(destination),
        uploaded_by=current_user.id,
        is_current=True,
    )
    db.add(asset)
    db.flush()
    db.add(AssetStorageLocation(
        asset_id=asset.id,
        provider="local",
        storage_key=asset.storage_key,
        public_url=asset.public_url,
        status="active",
        is_primary=True,
        checksum_sha256=asset.checksum_sha256,
        size_bytes=asset.size_bytes,
    ))

    log_admin_activity(
        db, current_user, action="book.pdf_uploaded", entity_type="book",
        entity_id=book.id, metadata={"title": title, "filename": filename, "visibility": visibility},
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise

    db.refresh(book)
    return to_resource_read(book, include_assets=True)


@router.patch("/{book_id}/update-pdf", response_model=BookRead)
async def update_book_pdf_only(
    request: Request,
    book_id: int,
    pdf_file: UploadFile | None = File(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    pdf_file = pdf_file or file
    if pdf_file is None:
        raise HTTPException(status_code=400, detail="No PDF file was supplied. Expected multipart field 'pdf_file'.")

    settings = get_settings()

    validate_upload_file(
        pdf_file,
        allowed_content_types={"application/pdf"},
        max_size_mb=settings.max_pdf_upload_mb,
        label="PDF",
    )

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    filename, destination = await save_upload_file(
        pdf_file,
        destination_dir=BOOKS_STORAGE_DIR,
        fallback_filename="book.pdf",
        max_size_mb=settings.max_pdf_upload_mb,
        label="PDF",
    )

    source_url = build_public_static_url(f"/books/file/{filename}", request)

    book.source_type = "pdf"
    book.source_url = source_url
    book.source_path = str(destination)
    book.mime_type = "application/pdf"
    book.checksum_sha256 = compute_sha256(destination)
    book.digitized_at = datetime.now(timezone.utc)

    previous_assets = db.scalars(
        select(BookAsset).where(BookAsset.book_id == book.id, BookAsset.asset_type == "pdf", BookAsset.asset_role == "access", BookAsset.is_current.is_(True))
    ).all()
    for previous in previous_assets:
        _withdraw_current_access_asset(
            db, asset=previous, archival_object=book.archival_object, current_user=current_user,
            detail="PDF access version withdrawn after replacement.",
        )
    previous_version = db.scalar(
        select(func.max(BookAsset.version)).where(BookAsset.book_id == book.id, BookAsset.asset_type == "pdf", BookAsset.asset_role == "access")
    ) or 0
    asset = BookAsset(
        book_id=book.id, asset_type="pdf", asset_role="access", version=previous_version + 1,
        original_filename=pdf_file.filename or filename, storage_key=f"books/{filename}",
        public_url=source_url, mime_type="application/pdf", size_bytes=destination.stat().st_size,
        checksum_sha256=book.checksum_sha256 or compute_sha256(destination), uploaded_by=current_user.id, is_current=True,
    )
    db.add(asset)
    db.flush()
    if book.archival_object is not None:
        _invalidate_archival_rights_review(book.archival_object, book)
    db.add(AssetStorageLocation(
        asset_id=asset.id, provider="local", storage_key=asset.storage_key,
        public_url=asset.public_url, status="active", is_primary=True,
        checksum_sha256=asset.checksum_sha256, size_bytes=asset.size_bytes,
    ))

    log_admin_activity(
        db,
        current_user,
        action="book.pdf_replaced",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title, "filename": filename},
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    db.refresh(book)

    return to_resource_read(book, include_assets=True)


@router.patch("/{book_id}/update-text", response_model=BookRead)
async def update_book_text(
    book_id: int,
    text_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    """Replace a plain-text access representation as a new immutable asset version."""
    require_admin_user(current_user)
    book = db.scalar(select(Book).where(Book.id == book_id, Book.archived_at.is_(None)))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    settings = get_settings()
    validate_upload_file(text_file, {"text/plain", "text/markdown"}, settings.max_text_upload_mb, "Plain text")
    destination: Path | None = None
    try:
        filename, destination = await save_upload_file(
            text_file, BOOKS_STORAGE_DIR, "source.txt", settings.max_text_upload_mb, "Plain text",
        )
        try:
            content = destination.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="Text source must be valid UTF-8") from exc
        if not content.strip() or "\x00" in content:
            raise HTTPException(status_code=400, detail="Text source is empty or contains binary data")

        current_assets = db.scalars(select(BookAsset).where(
            BookAsset.book_id == book.id, BookAsset.asset_type == "text",
            BookAsset.asset_role == "access", BookAsset.is_current.is_(True),
            BookAsset.logical_key.is_(None),
        )).all()
        for previous in current_assets:
            _withdraw_current_access_asset(
                db, asset=previous, archival_object=book.archival_object, current_user=current_user,
                detail="Text access version withdrawn after replacement.",
            )
        version = _asset_version(db, book_id=book.id, asset_type="text", logical_key=None)
        checksum = compute_sha256(destination)
        asset = BookAsset(
            book_id=book.id, asset_type="text", asset_role="access", logical_key=None, version=version,
            original_filename=text_file.filename or filename, storage_key=f"books/{filename}", public_url=None,
            mime_type="text/plain; charset=utf-8", size_bytes=destination.stat().st_size,
            checksum_sha256=checksum, uploaded_by=current_user.id, is_current=True,
            source_asset_id=current_assets[0].id if current_assets else None,
            derivation_type="replacement",
        )
        db.add(asset)
        db.flush()
        _add_asset_storage_location(db, asset)
        book.source_type = "text"
        book.source_url = None
        book.source_path = str(destination)
        book.mime_type = "text/plain; charset=utf-8"
        book.content_text = content
        book.checksum_sha256 = checksum
        book.digitized_at = datetime.now(timezone.utc)
        if book.archival_object is not None:
            _invalidate_archival_rights_review(book.archival_object, book)
        log_admin_activity(db, current_user, action="book.text_replaced", entity_type="book", entity_id=book.id, metadata={"filename": filename, "version": version})
        db.commit()
        db.refresh(book)
        return to_resource_read(book, include_assets=True)
    except HTTPException:
        db.rollback()
        if destination:
            destination.unlink(missing_ok=True)
        raise
    except Exception:
        db.rollback()
        if destination:
            destination.unlink(missing_ok=True)
        raise


@router.patch("/{book_id}", response_model=BookRead)
def update_book_metadata(
    book_id: int,
    title: str | None = Form(None),
    author: str | None = Form(None),
    cover: str | None = Form(None),
    description: str | None = Form(None),
    rating: float | None = Form(None),
    pages: int | None = Form(None),
    genre_csv: str | None = Form(None),
    visibility: str | None = Form(None),
    subjects_csv: str | None = Form(None),
    language: str | None = Form(None),
    origin: str | None = Form(None),
    era: str | None = Form(None),
    original_format: str | None = Form(None),
    rights_statement: str | None = Form(None),
    condition_notes: str | None = Form(None),
    curator_note: str | None = Form(None),
    digitized_by: str | None = Form(None),
    accession_no: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if visibility is not None and visibility not in {"draft", "published"}:
        raise HTTPException(status_code=400, detail="Invalid visibility")
    if original_format is not None and original_format not in ORIGINAL_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid original_format")
    if rights_statement is not None and rights_statement not in RIGHTS_STATEMENTS:
        raise HTTPException(status_code=400, detail="Invalid rights_statement")

    if title is not None:
        book.title = title
    if author is not None:
        book.author = author
    if cover is not None:
        book.cover = cover
    if description is not None:
        book.description = description
    if rating is not None:
        book.rating = rating
    if pages is not None:
        book.pages = pages
    if genre_csv is not None:
        book.genres = [g.strip() for g in genre_csv.split(",") if g.strip()]
    if visibility is not None:
        book.visibility = visibility
    if subjects_csv is not None:
        book.subjects = [s.strip() for s in subjects_csv.split(",") if s.strip()]
    if language is not None:
        book.language = language
    if origin is not None:
        book.origin = origin
    if era is not None:
        book.era = era
    if original_format is not None:
        book.original_format = original_format
    if rights_statement is not None:
        book.rights_statement = rights_statement
    if condition_notes is not None:
        book.condition_notes = condition_notes
    if curator_note is not None:
        book.curator_note = curator_note
    if digitized_by is not None:
        book.digitized_by = digitized_by
    if accession_no is not None:
        book.accession_no = accession_no

    log_admin_activity(
        db,
        current_user,
        action="book.metadata_updated",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title},
    )

    db.commit()
    db.refresh(book)

    return to_resource_read(book)




@router.post("/{book_id}/cover", response_model=BookRead)
async def upload_book_cover(
    request: Request,
    book_id: int,
    cover_file: UploadFile | None = File(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    cover_file = cover_file or file
    if cover_file is None:
        raise HTTPException(status_code=400, detail="No cover file was supplied. Expected multipart field 'cover_file'.")

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    settings = get_settings()

    validate_upload_file(
        cover_file,
        allowed_content_types={"image/png", "image/jpeg", "image/webp"},
        max_size_mb=settings.max_cover_upload_mb,
        label="Cover",
    )

    filename, destination = await save_upload_file(
        cover_file,
        destination_dir=COVERS_STORAGE_DIR,
        fallback_filename="cover.jpg",
        max_size_mb=settings.max_cover_upload_mb,
        label="Cover",
    )

    cover_url = build_public_static_url(f"/static/covers/{filename}", request)

    book.cover = cover_url
    book.cover_path = str(destination)

    previous_assets = db.scalars(
        select(BookAsset).where(BookAsset.book_id == book.id, BookAsset.asset_type == "cover", BookAsset.asset_role == "access", BookAsset.is_current.is_(True))
    ).all()
    for previous in previous_assets:
        _withdraw_current_access_asset(
            db, asset=previous, archival_object=book.archival_object, current_user=current_user,
            detail="PDF access version withdrawn after replacement.",
        )
    previous_version = db.scalar(
        select(func.max(BookAsset.version)).where(BookAsset.book_id == book.id, BookAsset.asset_type == "cover", BookAsset.asset_role == "access")
    ) or 0
    asset = BookAsset(
        book_id=book.id, asset_type="cover", asset_role="access", version=previous_version + 1,
        original_filename=cover_file.filename or filename, storage_key=f"covers/{filename}",
        public_url=cover_url, mime_type=cover_file.content_type or "image/jpeg", size_bytes=destination.stat().st_size,
        checksum_sha256=compute_sha256(destination), uploaded_by=current_user.id, is_current=True,
    )
    db.add(asset)
    db.flush()
    db.add(AssetStorageLocation(
        asset_id=asset.id, provider="local", storage_key=asset.storage_key,
        public_url=asset.public_url, status="active", is_primary=True,
        checksum_sha256=asset.checksum_sha256, size_bytes=asset.size_bytes,
    ))

    log_admin_activity(
        db,
        current_user,
        action="book.cover_uploaded",
        entity_type="book",
        entity_id=book.id,
        metadata={"filename": filename},
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    db.refresh(book)

    return to_resource_read(book, include_assets=True)



@router.patch("/{book_id}/publish", response_model=BookRead)
def publish_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)
    book = db.scalar(select(Book).where(Book.id == book_id))
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.archived_at is not None:
        raise HTTPException(status_code=400, detail="Archived books cannot be published")
    has_current_canvas_asset = bool(
        book.archival_object
        and any(canvas.asset and canvas.asset.is_current and canvas.asset.asset_role == "access" for canvas in book.archival_object.canvases)
    )
    has_primary_document = bool(book.source_path)
    if not has_primary_document and not has_current_canvas_asset:
        raise HTTPException(status_code=400, detail="A supported digital representation (PDF, text, or archival image sequence) is required before publishing")
    if book.archival_object is not None:
        rights = book.archival_object.rights
        if rights is None or rights.verified_at is None or rights.view_allowed is None:
            raise HTTPException(status_code=409, detail="Complete the archival rights review before publishing this record")
        book.archival_object.visibility = "published" if rights.view_allowed is True else "restricted"
    book.visibility = "published"
    log_admin_activity(db, current_user, action="book.published", entity_type="book", entity_id=book.id, metadata={"title": book.title, "archival_object_visibility": book.archival_object.visibility if book.archival_object else None})
    db.commit()
    db.refresh(book)
    return to_resource_read(book, include_assets=True)


@router.patch("/{book_id}/archive", response_model=BookRead)
def archive_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.archived_at = datetime.now(timezone.utc)

    log_admin_activity(
        db,
        current_user,
        action="book.archived",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title},
    )

    db.commit()
    db.refresh(book)

    return to_book_read(book)



@router.patch("/{book_id}/restore", response_model=BookRead)
def restore_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookRead:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.archived_at = None

    log_admin_activity(
        db,
        current_user,
        action="book.restored",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title},
    )

    db.commit()
    db.refresh(book)

    return to_book_read(book)


@router.delete("/{book_id}", status_code=204)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    require_admin_user(current_user)

    book = db.scalar(select(Book).where(Book.id == book_id))

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    title = book.title

    assets = db.scalars(select(BookAsset).where(BookAsset.book_id == book.id)).all()
    paths = {asset.storage_key for asset in assets}
    if book.source_path:
        paths.add(book.source_path)
    if getattr(book, "cover_path", None):
        paths.add(book.cover_path)
    for path in paths:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = Path(get_settings().storage_dir) / candidate
        if candidate.exists():
            try:
                candidate.unlink()
            except OSError:
                pass

    db.delete(book)

    log_admin_activity(
        db,
        current_user,
        action="book.deleted",
        entity_type="book",
        entity_id=book_id,
        metadata={"title": title},
    )

    db.commit()
