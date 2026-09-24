import os
import math
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    Query,
)
from sqlalchemy import select, case, func, or_
from sqlalchemy.orm import Session
from app.models.library_item import LibraryItem
from app.core.database import get_db
from app.core.storage import (
    BOOKS_STORAGE_DIR,
    COVERS_STORAGE_DIR,
    build_public_file_url,
    ensure_storage_dirs,
)
from app.models.book import Book, RIGHTS_STATEMENTS, ORIGINAL_FORMATS
from app.models.book_asset import BookAsset
from app.schemas.book import BookContentRead, BookRead, AdminBookListRead, BookFacets
from app.models.user import User
from app.core.authz import require_admin_user
from app.core.security import get_current_user

from app.services.admin_activity import log_admin_activity
from app.models.admin_activity_log import AdminActivityLog
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


def public_books_stmt():
    return (
        select(Book)
        .where(Book.archived_at.is_(None))
        .where(Book.visibility == "published")
    )


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

    rows = db.scalars(stmt.order_by(Book.id.desc()).offset(offset).limit(limit)).all()

    return AdminBookListRead(
        items=[to_book_read(row) for row in rows],
        total=total,
        page=safe_page,
        limit=limit,
        pages=pages,
    )


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
            (LibraryItem.book_id == Book.id) & (LibraryItem.updated_at >= since),
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
            (LibraryItem.book_id == Book.id) & (LibraryItem.updated_at >= since),
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
    preferred_genres = (
        {value.strip().lower() for value in (settings.preferred_genres or [])}
        if settings
        else set()
    )
    goals = (
        {value.strip().lower() for value in (settings.reading_goals or [])}
        if settings
        else set()
    )
    styles = (
        {value.strip().lower() for value in (settings.content_styles or [])}
        if settings
        else set()
    )
    lengths = (
        {value.strip().lower() for value in (settings.preferred_lengths or [])}
        if settings
        else set()
    )

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
        haystack = " ".join(
            [
                book.title,
                book.description,
                *book.genres,
                *book.tags,
                *book.subjects,
            ]
        ).lower()
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

    scored.sort(
        key=lambda item: (item[0], item[1].rating or 0, item[1].id), reverse=True
    )
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
    rows = db.scalars(public_books_stmt().order_by(Book.id.desc())).all()

    return [to_book_read(row) for row in rows]


@router.get("/{book_id}", response_model=BookRead)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookRead:
    row = db.scalar(public_books_stmt().where(Book.id == book_id))

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
        raise HTTPException(
            status_code=400, detail="Only published books can be featured"
        )

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
    rows = discover_books(
        q=q, genre=genre, sort="recommended", limit=100, offset=0, db=db
    )

    categories = {genre_item for book in rows for genre_item in book.genre}

    return {
        "visible_books": len(rows),
        "top_rated": len([book for book in rows if book.rating >= 4.5]),
        "new_this_week": min(len(rows), 6),
        "categories": len(categories),
    }


@router.get("/{book_id}/content", response_model=BookContentRead)
def get_book_content(book_id: int, db: Session = Depends(get_db)) -> BookContentRead:
    row = db.scalar(public_books_stmt().where(Book.id == book_id))
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")

    return BookContentRead(
        id=row.id,
        title=row.title,
        source_type=row.source_type,
        content_type=row.content_type,
        mime_type=row.mime_type,
        source_url=row.source_url,
        content_text=row.content_text,
    )


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

    source_url = build_public_static_url(f"/static/books/{filename}", request)

    cover_url = cover or build_public_static_url(
        "/static/assets/book-placeholder.svg", request
    )

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

    log_admin_activity(
        db,
        current_user,
        action="book.pdf_uploaded",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": title, "filename": filename, "visibility": visibility},
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
        raise HTTPException(
            status_code=400,
            detail="No PDF file was supplied. Expected multipart field 'pdf_file'.",
        )

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

    source_url = build_public_static_url(f"/static/books/{filename}", request)

    book.source_type = "pdf"
    book.source_url = source_url
    book.source_path = str(destination)
    book.mime_type = "application/pdf"
    book.checksum_sha256 = compute_sha256(destination)
    book.digitized_at = datetime.now(timezone.utc)

    previous_assets = db.scalars(
        select(BookAsset).where(
            BookAsset.book_id == book.id,
            BookAsset.asset_type == "pdf",
            BookAsset.asset_role == "access",
            BookAsset.is_current.is_(True),
        )
    ).all()
    for previous in previous_assets:
        previous.is_current = False
    previous_version = (
        db.scalar(
            select(func.max(BookAsset.version)).where(
                BookAsset.book_id == book.id,
                BookAsset.asset_type == "pdf",
                BookAsset.asset_role == "access",
            )
        )
        or 0
    )
    db.add(
        BookAsset(
            book_id=book.id,
            asset_type="pdf",
            asset_role="access",
            version=previous_version + 1,
            original_filename=pdf_file.filename or filename,
            storage_key=f"books/{filename}",
            public_url=source_url,
            mime_type="application/pdf",
            size_bytes=destination.stat().st_size,
            checksum_sha256=book.checksum_sha256 or compute_sha256(destination),
            uploaded_by=current_user.id,
            is_current=True,
        )
    )

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
        raise HTTPException(
            status_code=400,
            detail="No cover file was supplied. Expected multipart field 'cover_file'.",
        )

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
        select(BookAsset).where(
            BookAsset.book_id == book.id,
            BookAsset.asset_type == "cover",
            BookAsset.asset_role == "access",
            BookAsset.is_current.is_(True),
        )
    ).all()
    for previous in previous_assets:
        previous.is_current = False
    previous_version = (
        db.scalar(
            select(func.max(BookAsset.version)).where(
                BookAsset.book_id == book.id,
                BookAsset.asset_type == "cover",
                BookAsset.asset_role == "access",
            )
        )
        or 0
    )
    db.add(
        BookAsset(
            book_id=book.id,
            asset_type="cover",
            asset_role="access",
            version=previous_version + 1,
            original_filename=cover_file.filename or filename,
            storage_key=f"covers/{filename}",
            public_url=cover_url,
            mime_type=cover_file.content_type or "image/jpeg",
            size_bytes=destination.stat().st_size,
            checksum_sha256=compute_sha256(destination),
            uploaded_by=current_user.id,
            is_current=True,
        )
    )

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
        raise HTTPException(
            status_code=400, detail="Archived books cannot be published"
        )
    if not book.source_path:
        raise HTTPException(
            status_code=400, detail="A digital document is required before publishing"
        )
    book.visibility = "published"
    log_admin_activity(
        db,
        current_user,
        action="book.published",
        entity_type="book",
        entity_id=book.id,
        metadata={"title": book.title},
    )
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
